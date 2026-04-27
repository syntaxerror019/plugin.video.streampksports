"""
Streamed Sports Kodi Addon
Scrapes embed pages to extract actual video URLs
"""
import sys
import urllib.parse
import traceback
import json
import re
from datetime import datetime
import xbmcplugin
import xbmcgui
import xbmcaddon
import xbmc
from resources.lib.api import StreamedAPI

ADDON_URL = sys.argv[0]
ADDON_HANDLE = int(sys.argv[1])
ADDON_ARGS = urllib.parse.parse_qs(sys.argv[2][1:])

api = StreamedAPI()
addon = xbmcaddon.Addon()

xbmc.log("[StreamedSports] Addon started", xbmc.LOGINFO)


def build_url(query_params):
    """Build a plugin URL with the given query parameters."""
    return f"{ADDON_URL}?{urllib.parse.urlencode(query_params)}"


def add_directory_item(title, url, thumb=None, info_labels=None, is_folder=True):
    """Add a navigable item to the Kodi directory listing."""
    try:
        list_item = xbmcgui.ListItem(label=title)
        if thumb:
            list_item.setArt({"thumb": thumb, "icon": thumb})
        if info_labels:
            list_item.setInfo("video", info_labels)
        if not is_folder:
            list_item.setProperty("IsPlayable", "true")
        
        xbmcplugin.addDirectoryItem(
            handle=ADDON_HANDLE,
            url=url,
            listitem=list_item,
            isFolder=is_folder
        )
    except Exception as e:
        xbmc.log(f"[StreamedSports] Error adding item: {str(e)}", xbmc.LOGERROR)


def show_sports_menu():
    """Display all sports categories from /api/sports"""
    xbmc.log("[StreamedSports] Loading sports menu", xbmc.LOGINFO)
    
    try:
        sports = api.get_sports()
        
        if not sports:
            xbmcgui.Dialog().notification("Streamed Sports", "Failed to load sports", xbmcgui.NOTIFICATION_ERROR)
            xbmcplugin.endOfDirectory(ADDON_HANDLE)
            return
        
        for sport in sports:
            sport_id = sport.get("id")
            sport_name = sport.get("name", "Unknown")
            
            url = build_url({
                "mode": "sport_matches",
                "sport_id": sport_id,
                "sport_name": sport_name
            })
            
            add_directory_item(
                title=sport_name,
                url=url,
                info_labels={"title": sport_name, "plot": f"Browse {sport_name} matches"}
            )
        
        # Add global categories
        add_directory_item(
            title="🔴 Live Now",
            url=build_url({"mode": "live_matches"}),
            info_labels={"title": "Live Now", "plot": "Currently live matches across all sports"}
        )
        
        add_directory_item(
            title="📅 Today's Matches",
            url=build_url({"mode": "todays_matches"}),
            info_labels={"title": "Today's Matches", "plot": "All matches scheduled for today"}
        )
        
        add_directory_item(
            title="🌍 All Matches",
            url=build_url({"mode": "all_matches"}),
            info_labels={"title": "All Matches", "plot": "Browse all available matches"}
        )
        
        xbmcplugin.addSortMethod(ADDON_HANDLE, xbmcplugin.SORT_METHOD_LABEL)
        
    except Exception as e:
        xbmc.log(f"[StreamedSports] Error in sports menu: {str(e)}", xbmc.LOGERROR)
        xbmc.log(traceback.format_exc(), xbmc.LOGERROR)
    
    xbmcplugin.endOfDirectory(ADDON_HANDLE)


def show_matches(matches, title=""):
    """Display a list of matches from the API."""
    if not matches:
        xbmcgui.Dialog().notification("Streamed Sports", "No matches found", xbmcgui.NOTIFICATION_INFO)
        xbmcplugin.endOfDirectory(ADDON_HANDLE)
        return
    
    for match in matches:
        match_id = match.get("id", "")
        match_title = match.get("title", "Unknown Match")
        category = match.get("category", "")
        match_date = match.get("date")
        poster = match.get("poster")
        teams = match.get("teams")
        sources = match.get("sources", [])
        
        display_title = match_title
        
        if match_date:
            dt = datetime.fromtimestamp(match_date / 1000)
            if dt.date() == datetime.now().date():
                time_str = f"Today {dt.strftime('%H:%M')}"
            else:
                time_str = dt.strftime("%Y-%m-%d %H:%M")
            display_title = f"{display_title} [{time_str}]"
        
        if sources:
            url = build_url({
                "mode": "show_sources",
                "match_id": match_id,
                "match_title": match_title,
                "sources": json.dumps(sources)
            })
            is_folder = True
        else:
            url = build_url({"mode": "empty"})
            is_folder = False
        
        thumb_url = None
        if poster:
            thumb_url = api.get_image_url(poster, "poster")
        elif teams:
            home_team = teams.get("home", {})
            if home_team.get("badge"):
                thumb_url = api.get_image_url(home_team["badge"], "badge")
        
        plot_lines = [f"Sport: {category}"]
        if teams:
            home = teams.get("home", {})
            away = teams.get("away", {})
            if home.get("name"):
                plot_lines.append(f"Home: {home['name']}")
            if away.get("name"):
                plot_lines.append(f"Away: {away['name']}")
        plot_lines.append(f"Available streams: {len(sources)}")
        
        info_labels = {
            "title": match_title,
            "plot": "\n".join(plot_lines),
            "genre": category
        }
        
        add_directory_item(
            title=display_title,
            url=url,
            thumb=thumb_url,
            info_labels=info_labels,
            is_folder=is_folder
        )
    
    xbmcplugin.addSortMethod(ADDON_HANDLE, xbmcplugin.SORT_METHOD_DATE)
    xbmcplugin.endOfDirectory(ADDON_HANDLE)


def show_sources(match_id, match_title, sources_json):
    """Show stream source options for a match."""
    try:
        sources = json.loads(sources_json)
    except:
        xbmc.log("[StreamedSports] Failed to parse sources", xbmc.LOGERROR)
        xbmcplugin.endOfDirectory(ADDON_HANDLE)
        return
    
    if not sources:
        xbmcgui.Dialog().notification("Streamed Sports", "No sources available", xbmcgui.NOTIFICATION_INFO)
        xbmcplugin.endOfDirectory(ADDON_HANDLE)
        return
    
    for source in sources:
        source_name = source.get("source", "unknown")
        source_id = source.get("id", "")
        
        url = build_url({
            "mode": "show_streams",
            "source": source_name,
            "source_id": source_id,
            "match_title": match_title
        })
        
        add_directory_item(
            title=f"📺 {source_name.upper()} Stream",
            url=url,
            info_labels={
                "title": f"{match_title} - {source_name}",
                "plot": f"Source: {source_name}\nClick to see available streams"
            }
        )
    
    xbmcplugin.addSortMethod(ADDON_HANDLE, xbmcplugin.SORT_METHOD_LABEL)
    xbmcplugin.endOfDirectory(ADDON_HANDLE)


def show_streams_for_source(source, source_id, match_title):
    """Show individual streams for a specific source."""
    xbmc.log(f"[StreamedSports] Loading streams for {source}/{source_id}", xbmc.LOGINFO)
    
    streams = api.get_streams(source, source_id)
    
    if not streams:
        xbmcgui.Dialog().notification("Streamed Sports", "No streams available", xbmcgui.NOTIFICATION_INFO)
        xbmcplugin.endOfDirectory(ADDON_HANDLE)
        return
    
    for stream in streams:
        stream_id = stream.get("id", "")
        stream_no = stream.get("streamNo", "")
        language = stream.get("language", "Unknown")
        hd = stream.get("hd", False)
        embed_url = stream.get("embedUrl", "")
        
        quality = "HD" if hd else "SD"
        display_title = f"Stream #{stream_no} - {language} [{quality}]"
        
        # Pass the embed URL to the resolver
        url = build_url({
            "mode": "resolve_and_play",
            "embed_url": embed_url,
            "title": f"{match_title} - {language} ({quality})"
        })
        
        add_directory_item(
            title=display_title,
            url=url,
            info_labels={
                "title": f"Stream {stream_no}",
                "plot": f"Language: {language}\nQuality: {quality}"
            },
            is_folder=False
        )
    
    xbmcplugin.addSortMethod(ADDON_HANDLE, xbmcplugin.SORT_METHOD_LABEL)
    xbmcplugin.endOfDirectory(ADDON_HANDLE)


def resolve_and_play(embed_url, title):
    import subprocess, os, sys, time, json
    import urllib.request, urllib.error
    import xbmc, xbmcgui, xbmcaddon, xbmcplugin

    # Display progress dialog
    dialog = xbmcgui.DialogProgress()
    dialog.create("Streamed Sports", "Initializing stream proxy...")
    dialog.update(10)

    # Clean up old proxy instances
    try:
        # Quick shell command to kill any process listening on 8081
        subprocess.run(["fuser", "-k", "8081/tcp"], stderr=subprocess.DEVNULL, stdout=subprocess.DEVNULL)
    except:
        pass
        
    dialog.update(30, "Starting background extractor...")
    
    # Get addon path to find extractor_proxy.py
    addon = xbmcaddon.Addon()
    addon_path = addon.getAddonInfo('path')
    proxy_script = os.path.join(addon_path, "extractor_proxy.py")

    # Launch proxy
    proxy_process = subprocess.Popen([sys.executable, proxy_script, embed_url], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    
    # Wait for proxy to become ready
    ready = False
    timeout = 40  # Wait up to 40 seconds
    for i in range(timeout):
        if dialog.iscanceled():
            proxy_process.kill()
            return
            
        dialog.update(30 + int(60 * (i / timeout)), f"Waiting for stream... ({i}/{timeout}s)")
        
        try:
            req = urllib.request.Request("http://127.0.0.1:8081/status")
            with urllib.request.urlopen(req, timeout=2) as response:
                if response.getcode() == 200:
                    data = json.loads(response.read().decode())
                    if data.get("ready"):
                        ready = True
                        break
        except (urllib.error.URLError, ConnectionResetError, json.JSONDecodeError):
            pass
            
        time.sleep(1)

    dialog.close()

    if ready:
        xbmc.log("[StreamedSports] Proxy ready. Handing off to Kodi player.", xbmc.LOGINFO)
        # Create a playable listitem
        play_item = xbmcgui.ListItem(path="http://127.0.0.1:8081/stream")
        # Play the item using setResolvedUrl
        xbmcplugin.setResolvedUrl(ADDON_HANDLE, True, listitem=play_item)
    else:
        xbmc.log("[StreamedSports] Proxy timed out or failed to start", xbmc.LOGERROR)
        proxy_process.kill()
        xbmcgui.Dialog().notification("Streamed Sports", "Failed to load stream (Timeout)", xbmcgui.NOTIFICATION_ERROR)
        xbmcplugin.setResolvedUrl(ADDON_HANDLE, False, listitem=xbmcgui.ListItem())

def router():
    """Route to the correct function based on mode parameter."""
    try:
        mode = ADDON_ARGS.get("mode", [None])[0]
        xbmc.log(f"[StreamedSports] Mode: {mode}", xbmc.LOGINFO)
        
        if mode is None:
            show_sports_menu()
        
        elif mode == "sport_matches":
            sport_id = ADDON_ARGS.get("sport_id", [""])[0]
            sport_name = ADDON_ARGS.get("sport_name", ["Sport"])[0]
            xbmcplugin.setPluginCategory(ADDON_HANDLE, sport_name)
            matches = api.get_matches_by_sport(sport_id)
            show_matches(matches)
        
        elif mode == "all_matches":
            xbmcplugin.setPluginCategory(ADDON_HANDLE, "All Matches")
            matches = api.get_all_matches()
            show_matches(matches)
        
        elif mode == "todays_matches":
            xbmcplugin.setPluginCategory(ADDON_HANDLE, "Today's Matches")
            matches = api.get_todays_matches()
            show_matches(matches)
        
        elif mode == "live_matches":
            xbmcplugin.setPluginCategory(ADDON_HANDLE, "Live Now")
            matches = api.get_live_matches()
            show_matches(matches)
        
        elif mode == "show_sources":
            match_id = ADDON_ARGS.get("match_id", [""])[0]
            match_title = ADDON_ARGS.get("match_title", ["Match"])[0]
            sources = ADDON_ARGS.get("sources", ["[]"])[0]
            show_sources(match_id, match_title, sources)
        
        elif mode == "show_streams":
            source = ADDON_ARGS.get("source", [""])[0]
            source_id = ADDON_ARGS.get("source_id", [""])[0]
            match_title = ADDON_ARGS.get("match_title", ["Match"])[0]
            show_streams_for_source(source, source_id, match_title)
        
        elif mode == "resolve_and_play":
            embed_url = ADDON_ARGS.get("embed_url", [""])[0]
            title = ADDON_ARGS.get("title", ["Stream"])[0]
            resolve_and_play(embed_url, title)
        
        else:
            xbmc.log(f"[StreamedSports] Unknown mode: {mode}", xbmc.LOGWARNING)
    
    except Exception as e:
        xbmc.log(f"[StreamedSports] Router error: {str(e)}", xbmc.LOGERROR)
        xbmc.log(traceback.format_exc(), xbmc.LOGERROR)
        xbmcgui.Dialog().notification("Streamed Sports", f"Error: {str(e)}", xbmcgui.NOTIFICATION_ERROR)


if __name__ == "__main__":
    router()