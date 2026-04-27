import os
import time
import threading
import subprocess
from flask import Flask, Response
from playwright.sync_api import sync_playwright

app = Flask(__name__)
video_chunks = []
init_chunks_v = []
audio_chunks = []
init_chunks_a = []
chunk_cond = threading.Condition()

def stream_generator(chunks_list, init_list):
    with chunk_cond:
        # We need the initialization chunks (ftyp/moov boxes) first so the player/ffmpeg can probe
        chunks_to_send = list(init_list)
        # Add the last 30 chunks so we are close to the live edge
        start_idx = max(0, len(chunks_list) - 30)
        chunks_to_send.extend(chunks_list[start_idx:])
        last_index = len(chunks_list)
        
    for chunk in chunks_to_send:
        yield chunk
        
    while True:
        with chunk_cond:
            while last_index >= len(chunks_list):
                chunk_cond.wait()
            chunks_to_send = chunks_list[last_index:]
            last_index = len(chunks_list)
        
        for chunk in chunks_to_send:
            yield chunk

@app.route('/video')
def video_stream():
    return Response(stream_generator(video_chunks, init_chunks_v), mimetype="video/mp4")

@app.route('/audio')
def audio_stream():
    return Response(stream_generator(audio_chunks, init_chunks_a), mimetype="audio/mp4")

@app.route('/status')
def status():
    # Return 200 OK and ready=true only if video chunks have started buffering
    return {"ready": len(video_chunks) > 0}

connected_event = threading.Event()

def timeout_check():
    # Auto-shutdown if Kodi does not connect to /stream within 60 seconds
    if not connected_event.wait(60):
        print("[!] No client connected within 60 seconds. Auto-shutting down...")
        os._exit(0)

active_connections = 0
shutdown_timer = None

def schedule_shutdown():
    global shutdown_timer
    def do_shutdown():
        if active_connections == 0:
            print("[*] No active connections for 15s. Shutting down.")
            os._exit(0)
    shutdown_timer = threading.Timer(15.0, do_shutdown)
    shutdown_timer.start()

def cancel_shutdown():
    global shutdown_timer
    if shutdown_timer:
        shutdown_timer.cancel()
        shutdown_timer = None

@app.route('/stream')
def multiplexed_stream():
    connected_event.set()
    
    # VLC/Kodi hits this endpoint.
    def generate():
        global active_connections
        active_connections += 1
        cancel_shutdown()
        
        print(f"[*] Client connected to /stream. Active connections: {active_connections}")
        
        # Wait up to 30 seconds for chunks to arrive so we don't start FFmpeg prematurely
        for _ in range(60):
            if len(video_chunks) > 0:
                break
            time.sleep(0.5)
            
        # Give audio an extra second to show up if it's slightly delayed
        time.sleep(1)
        has_audio = len(audio_chunks) > 0
        
        print(f"[*] Starting FFmpeg multiplexer. Audio detected: {has_audio}")
        
        cmd = ['ffmpeg', '-re', '-f', 'mp4', '-i', 'http://127.0.0.1:8081/video']
        if has_audio:
            cmd.extend(['-f', 'mp4', '-i', 'http://127.0.0.1:8081/audio'])
            # Explicitly map input 0 video and input 1 audio
            cmd.extend(['-map', '0:v:0', '-map', '1:a:0'])
        else:
            cmd.extend(['-map', '0:v:0'])
            
        # Copy codecs, mux into MPEG-TS
        cmd.extend(['-c', 'copy', '-f', 'mpegts', 'pipe:1'])
        
        process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)
        try:
            while True:
                data = process.stdout.read(8192)
                if not data:
                    print("[*] FFmpeg multiplexer finished or client disconnected.")
                    break
                yield data
        finally:
            process.kill()
            active_connections -= 1
            print(f"[*] Stream disconnected. Active connections: {active_connections}")
            if active_connections == 0:
                schedule_shutdown()

    return Response(generate(), mimetype="video/MP2T")

def run_browser(url):
    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=True,
            channel="chrome",
            args=["--no-sandbox", "--disable-setuid-sandbox", "--disable-web-security"]
        )
        context = browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        )
        
        page = context.new_page()
        
        # Block popups automatically
        def handle_new_page(new_page):
            if new_page != page:
                print("[*] Blocked popup ad")
                new_page.close()
        context.on("page", handle_new_page)
        
        # Log browser console
        page.on("console", lambda msg: print(f"[BROWSER] {msg.text}"))
        
        # Intercept the chunk POST requests natively in Playwright
        def handle_chunk_route(route):
            url = route.request.url
            is_audio = "type=audio" in url
            post_data = route.request.post_data_buffer
            
            if post_data:
                type_str = "AUDIO" if is_audio else "VIDEO"
                # print(f"[*] Received {type_str} chunk of size {len(post_data)} bytes")
                with chunk_cond:
                    if is_audio:
                        if len(init_chunks_a) < 2:
                            init_chunks_a.append(post_data)
                        audio_chunks.append(post_data)
                        if len(audio_chunks) > 500:
                            audio_chunks.pop(0)
                    else:
                        if len(init_chunks_v) < 2:
                            init_chunks_v.append(post_data)
                        video_chunks.append(post_data)
                        if len(video_chunks) > 500:
                            video_chunks.pop(0)
                    chunk_cond.notify_all()
            route.fulfill(status=200, body="OK")
            
        context.route("**/__intercept_chunk__*", handle_chunk_route)

        # Inject script to intercept appendBuffer and identify audio vs video
        page.add_init_script("""
            console.log("Playwright appendBuffer interceptor injected!");
            
            // Track SourceBuffers by mime type when they are added
            const origAddSourceBuffer = MediaSource.prototype.addSourceBuffer;
            MediaSource.prototype.addSourceBuffer = function(mime) {
                const sb = origAddSourceBuffer.call(this, mime);
                sb.__myType = (mime && mime.includes('audio')) ? 'audio' : 'video';
                return sb;
            };

            const origAppend = SourceBuffer.prototype.appendBuffer;
            SourceBuffer.prototype.appendBuffer = function(source) {
                try {
                    let type = this.__myType || 'video';
                    let data = source;
                    if (source instanceof ArrayBuffer) {
                        data = new Uint8Array(source);
                    } else if (source && source.buffer) {
                        data = new Uint8Array(source.buffer, source.byteOffset, source.byteLength);
                    }
                    if (data && data.length > 0) {
                        const blob = new Blob([data]);
                        let url = '/__intercept_chunk__?type=' + type;
                        if (window.location.origin !== 'null' && window.location.origin !== 'file://') {
                            url = window.location.origin + url;
                        }
                        fetch(url, {
                            method: 'POST',
                            body: blob
                        }).catch(e => console.error("Chunk proxy error", e.toString()));
                    }
                } catch(e) {
                    console.error("Interceptor error", e.toString());
                }
                return origAppend.call(this, source);
            };
        """)

        print(f"[*] Navigating to {url}...")
        try:
            page.goto(url, wait_until="load", timeout=20000)
        except Exception as e:
            print("[!] Navigation warning:", e)

        print("[*] Waiting for video player...")
        page.wait_for_timeout(3000)
        
        for frame in page.frames:
            try:
                frame.click("body")
                page.wait_for_timeout(1000)
            except:
                pass

        print("[*] Browser running. Intercepting chunks...")
        print("[*] Press Ctrl+C to stop.")
        
        while True:
            time.sleep(1)

if __name__ == '__main__':
    import sys
    import urllib.parse
    
    target_url = None
    if len(sys.argv) > 1:
        target_url = sys.argv[1]
        
    # Append autoplay params to URL to ensure the player starts automatically
    parsed_url = urllib.parse.urlparse(target_url)
    query_params = urllib.parse.parse_qsl(parsed_url.query)
    query_params.extend([
        ('autoplay', '1'),
        ('autostart', 'true'),
        ('mute', '0'),
        ('muted', '0'),
        ('volume', '100')
    ])
    new_query = urllib.parse.urlencode(query_params)
    target_url = urllib.parse.urlunparse((
        parsed_url.scheme,
        parsed_url.netloc,
        parsed_url.path,
        parsed_url.params,
        new_query,
        parsed_url.fragment
    ))
    target_url = target_url + "#player=clappr#autoplay=true#mute=false"
    
    # Start timeout checker
    threading.Thread(target=timeout_check, daemon=True).start()
    
    t = threading.Thread(target=run_browser, args=(target_url,), daemon=True)
    t.start()
    
    print("[*] Starting local proxy on http://127.0.0.1:8081")
    print("[*] Open VLC -> Network Stream -> http://127.0.0.1:8081/stream to play.")
    
    app.run(host="127.0.0.1", port=8081, threaded=True, debug=False)
