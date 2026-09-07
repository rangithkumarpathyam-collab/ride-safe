"""
SafeRide AI - Module 3: Reverse Geocoding & GIS Address Resolver (geocoding.py)
-------------------------------------------------------------------------------
Converts raw GPS telemetry coordinates (latitude, longitude) into human-readable
street addresses and landmark descriptions for emergency dispatchers.

Supports:
  1. Geoapify Reverse Geocoding API (Primary)
  2. OpenStreetMap Nominatim Reverse Geocoding (Automatic Fallback)
  3. Formatted Coordinate Reference (Offline Fallback)
"""

import os
import requests
from typing import Dict, Any, Optional
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

GEOAPIFY_API_KEY = os.getenv("GEOAPIFY_API_KEY") or os.getenv("GOOGLE_MAPS_API_KEY", "")

# In-memory coordinate cache to reduce external API round-trips
_GEO_CACHE: Dict[str, Dict[str, Any]] = {}


def reverse_geocode(lat: float, lon: float, timeout: int = 5) -> Dict[str, Any]:
    """
    Resolves GPS latitude and longitude into a detailed physical location.
    
    Returns:
        dict with keys:
          - formatted_address: str
          - landmark: str
          - city: str
          - state: str
          - provider: str
          - success: bool
    """
    cache_key = f"{round(lat, 4)},{round(lon, 4)}"
    if cache_key in _GEO_CACHE:
        return _GEO_CACHE[cache_key]

    # 1. Attempt Geoapify Geocoding API
    if GEOAPIFY_API_KEY and len(GEOAPIFY_API_KEY.strip()) >= 20:
        try:
            url = f"https://api.geoapify.com/v1/geocode/reverse?lat={lat}&lon={lon}&apiKey={GEOAPIFY_API_KEY.strip()}"
            resp = requests.get(url, timeout=timeout)
            if resp.status_code == 200:
                data = resp.json()
                features = data.get("features", [])
                if features:
                    props = features[0].get("properties", {})
                    formatted = props.get("formatted") or props.get("address_line1", "")
                    city = props.get("city") or props.get("county") or "Hyderabad"
                    state = props.get("state") or "Telangana"
                    landmark = props.get("name") or props.get("street") or "Near Incident Site"
                    
                    result = {
                        "formatted_address": formatted,
                        "landmark": landmark,
                        "city": city,
                        "state": state,
                        "provider": "Geoapify",
                        "success": True
                    }
                    _GEO_CACHE[cache_key] = result
                    return result
        except Exception as e:
            # Fallthrough to next provider
            pass

    # 2. Attempt OpenStreetMap Nominatim (Free, standard fallback)
    try:
        url = f"https://nominatim.openstreetmap.org/reverse?lat={lat}&lon={lon}&format=json"
        headers = {"User-Agent": "SafeRideAI-EmergencyDispatch/1.0"}
        resp = requests.get(url, headers=headers, timeout=timeout)
        if resp.status_code == 200:
            data = resp.json()
            address_dict = data.get("address", {})
            formatted = data.get("display_name", "")
            city = address_dict.get("city") or address_dict.get("town") or address_dict.get("suburb", "Hyderabad")
            state = address_dict.get("state", "Telangana")
            landmark = address_dict.get("road") or address_dict.get("neighbourhood", "Incident Coordinate")

            result = {
                "formatted_address": formatted,
                "landmark": landmark,
                "city": city,
                "state": state,
                "provider": "OpenStreetMap Nominatim",
                "success": True
            }
            _GEO_CACHE[cache_key] = result
            return result
    except Exception:
        pass

    # 3. Offline coordinate reference fallback
    fallback_result = {
        "formatted_address": f"GPS Sector ({round(lat, 5)}° N, {round(lon, 5)}° E)",
        "landmark": f"Coordinates [{round(lat, 4)}, {round(lon, 4)}]",
        "city": "Cyberabad Dispatch Zone",
        "state": "Telangana",
        "provider": "Offline Coordinate Engine",
        "success": False
    }
    _GEO_CACHE[cache_key] = fallback_result
    return fallback_result


def verify_geocoding_status() -> Dict[str, Any]:
    """
    Checks the active geocoding service status and tests reverse lookup.
    """
    test_lat, test_lon = 17.4435, 78.3772
    result = reverse_geocode(test_lat, test_lon)
    return {
        "configured": bool(GEOAPIFY_API_KEY and len(GEOAPIFY_API_KEY) > 10),
        "api_key_masked": f"{GEOAPIFY_API_KEY[:6]}...{GEOAPIFY_API_KEY[-4:]}" if GEOAPIFY_API_KEY else "Not Configured",
        "provider": result.get("provider", "Unknown"),
        "status": "ONLINE" if result.get("success") else "FALLBACK",
        "sample_address": result.get("formatted_address", "")
    }


def get_geoapify_static_map_url(
    lat: float,
    lon: float,
    zoom: int = 15,
    width: int = 640,
    height: int = 360,
    style: str = "dark-matter"
) -> str:
    """
    Generates a Geoapify Static Map URL for the accident location.
    Returns a JPEG image URL showing the crash site with a red marker.
    Works with the free Geoapify API key.
    
    Returns empty string if API key is not configured.
    """
    if not GEOAPIFY_API_KEY:
        return ""
    return (
        f"https://maps.geoapify.com/v1/staticmap"
        f"?style={style}&width={width}&height={height}"
        f"&center=lonlat:{lon},{lat}&zoom={zoom}"
        f"&marker=lonlat:{lon},{lat};color:%23ef4444;size:large;text:CRASH"
        f"&apiKey={GEOAPIFY_API_KEY}"
    )


if __name__ == "__main__":
    print("=== Testing SafeRide AI Geocoding Module ===")
    status = verify_geocoding_status()
    print("Status:", status)
    addr = reverse_geocode(17.4435, 78.3772)
    print("Resolved Address:", addr["formatted_address"])
    print("Static Map URL:", get_geoapify_static_map_url(17.4435, 78.3772))
