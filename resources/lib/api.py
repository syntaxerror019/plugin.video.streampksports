"""
Streamed Sports API Helper
Correctly implements the Streamed.pk API as documented
"""
import json
import xbmc
from urllib.request import Request, urlopen
from urllib.error import URLError, HTTPError
from urllib.parse import urljoin

BASE_URL = "https://streamed.pk/api"

class StreamedAPI:
    def __init__(self):
        xbmc.log("[StreamedSports] API Client Initialized", xbmc.LOGINFO)
    
    def _make_request(self, endpoint, params=None):
        """Make a GET request to the API."""
        url = urljoin(BASE_URL + "/", endpoint.lstrip("/"))
        
        xbmc.log(f"[StreamedSports] Requesting: {url}", xbmc.LOGINFO)
        
        try:
            req = Request(url)
            req.add_header('User-Agent', 'Kodi-StreamedSports/1.0')
            req.add_header('Accept', 'application/json')
            
            with urlopen(req, timeout=15) as response:
                data = response.read().decode('utf-8')
                return json.loads(data)
                
        except HTTPError as e:
            xbmc.log(f"[StreamedSports] HTTP Error {e.code}: {e.reason}", xbmc.LOGERROR)
            return None
        except URLError as e:
            xbmc.log(f"[StreamedSports] URL Error: {e.reason}", xbmc.LOGERROR)
            return None
        except Exception as e:
            xbmc.log(f"[StreamedSports] Error: {str(e)}", xbmc.LOGERROR)
            return None
    
    def get_sports(self):
        """GET /api/sports - Returns array of {id, name} objects"""
        return self._make_request("sports")
    
    def get_matches_by_sport(self, sport_id, popular=False):
        """GET /api/matches/[SPORT] or /api/matches/[SPORT]/popular"""
        endpoint = f"matches/{sport_id}"
        if popular:
            endpoint += "/popular"
        return self._make_request(endpoint)
    
    def get_all_matches(self, popular=False):
        """GET /api/matches/all or /api/matches/all/popular"""
        endpoint = "matches/all"
        if popular:
            endpoint += "/popular"
        return self._make_request(endpoint)
    
    def get_todays_matches(self, popular=False):
        """GET /api/matches/all-today or /api/matches/all-today/popular"""
        endpoint = "matches/all-today"
        if popular:
            endpoint += "/popular"
        return self._make_request(endpoint)
    
    def get_live_matches(self, popular=False):
        """GET /api/matches/live or /api/matches/live/popular"""
        endpoint = "matches/live"
        if popular:
            endpoint += "/popular"
        return self._make_request(endpoint)
    
    def get_streams(self, source, source_id):
        """GET /api/stream/[SOURCE]/[ID] - Returns array of stream objects
        Stream object: {id, streamNo, language, hd, embedUrl, source}
        """
        endpoint = f"stream/{source}/{source_id}"
        return self._make_request(endpoint)
    
    def get_image_url(self, image_path, image_type="badge"):
        """Construct full image URL based on the Images API.
        
        - Team badges: /api/images/badge/[id].webp
        - Match posters: /api/images/poster/[badge]/[badge].webp  
        - Proxied images: /api/images/proxy/[poster].webp
        """
        if not image_path:
            return None
        if image_path.startswith("http"):
            return image_path
        
        if image_type == "badge":
            return urljoin("https://streamed.pk/", f"api/images/badge/{image_path}.webp")
        elif image_type == "poster":
            return urljoin("https://streamed.pk/", f"api/images/proxy/{image_path}.webp")
        else:
            return urljoin("https://streamed.pk/", f"api/images/proxy/{image_path}.webp")