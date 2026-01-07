from __future__ import annotations
import os
import time
import requests
from typing import Optional, Dict, Any


NOMINATIM_SEARCH = "https://nominatim.openstreetmap.org/search"

HEADERS = {
    # Required by Nominatim policy: identify your app with a valid User-Agent
    "User-Agent": "CafeLocationOptimizer/1.0 (Python/requests)"
}


def nominatim_geocode(query: str, *, limit: int = 3, email: Optional[str] = None, countrycodes: Optional[str] = "gb") -> list[Dict[str, Any]]:
    """
    Geocode a query string using Nominatim.
    
    Args:
        query: Address or place name to geocode
        limit: Maximum number of results to return
        email: Optional email address (recommended for production use)
        countrycodes: Optional country code filter (e.g., "gb"). If None, searches globally.
        
    Returns:
        List of geocoding results
    """
    params = {
        "q": query,
        "format": "jsonv2",          # recommended structured JSON output
        "addressdetails": 1,
        "limit": limit,
    }
    
    # Add country filter if specified
    if countrycodes:
        params["countrycodes"] = countrycodes
    
    # Add email if provided (recommended by Nominatim for production use)
    if email:
        params["email"] = email

    r = requests.get(NOMINATIM_SEARCH, params=params, headers=HEADERS, timeout=20)
    
    # If 403 with countrycodes, try again without country restriction
    if r.status_code == 403 and countrycodes:
        print(f"Warning: 403 error with country filter, retrying without country restriction...")
        params.pop("countrycodes", None)
        time.sleep(1)  # Wait before retry
        r = requests.get(NOMINATIM_SEARCH, params=params, headers=HEADERS, timeout=20)
    
    if r.status_code == 403:
        raise RuntimeError(
            "403 Forbidden: Nominatim blocked the request. "
            "This may be due to rate limiting or User-Agent issues. "
            "Try adding an email parameter (set NOMINATIM_EMAIL env var) or wait a moment before retrying."
        )
    if r.status_code == 429:
        raise RuntimeError("Rate limited (429). Slow down to <= 1 req/sec and add caching.")
    
    r.raise_for_status()
    return r.json()


def geocode_address(
    address: str,
    city: Optional[str] = None,
    country: str = "UK",
    email: Optional[str] = None,
    countrycodes: Optional[str] = "gb"
) -> Optional[Dict[str, Any]]:
    """
    Geocode an address/place name and return coordinates.
    Tries multiple query formats for better results.
    
    Args:
        address: Address or place name (e.g., "Deansgate", "10 Norton Street", "Manchester Piccadilly Station")
        city: Optional city name to add context (e.g., "Manchester")
        country: Country name (default: "UK")
        email: Optional email address for Nominatim (recommended)
        countrycodes: Optional country code filter (e.g., "gb"). If None, searches globally.
        
    Returns:
        Dictionary with lat, lon, and metadata, or None if not found
    """
    import re
    
    # Detect if address already looks complete (has postcode, city name, etc.)
    # UK postcode pattern: letters + numbers (e.g., HA7, M1 1AA, SW1A 1AA)
    has_postcode = bool(re.search(r'\b[A-Z]{1,2}\d{1,2}[A-Z]?\s?\d[A-Z]{2}\b|\b[A-Z]{1,2}\d{1,2}[A-Z]?\b', address.upper()))
    
    # Common UK city/region names that indicate a complete address
    uk_locations = ['london', 'manchester', 'birmingham', 'liverpool', 'leeds', 'glasgow', 
                    'edinburgh', 'bristol', 'cardiff', 'belfast', 'greater london', 
                    'greater manchester', 'west midlands', 'south yorkshire', 'tyne and wear']
    has_location = any(loc in address.lower() for loc in uk_locations)
    
    # If address looks complete, try it as-is first
    queries_to_try = []
    
    if has_postcode or has_location or (',' in address and address.count(',') >= 2):
        # Address looks complete - try as-is first, then with minimal additions
        queries_to_try.append(address)  # Try exactly as provided
        if not has_postcode and country:
            queries_to_try.append(f"{address}, {country}")  # Just add country if needed
    else:
        # Address looks incomplete - build variations with city context
        if city:
            queries_to_try.append(f"{address}, {city}, {country}")
            queries_to_try.append(f"{address}, {city}")
        else:
            queries_to_try.append(f"{address}, {country}")
        queries_to_try.append(address)  # Also try as-is
    
    # Try each query variation until we get results
    debug = os.getenv("DEBUG_GEOCODE", "0") == "1"
    
    for i, query in enumerate(queries_to_try):
        if debug:
            print(f"  Trying query {i+1}/{len(queries_to_try)}: '{query}'")
        
        try:
            results = nominatim_geocode(query, limit=3, email=email, countrycodes=countrycodes)
            if results and len(results) > 0:
                if debug:
                    print(f"  ✓ Found result: {results[0].get('display_name', 'N/A')}")
                top = results[0]
                return {
                    "input": query,
                    "lat": float(top["lat"]),
                    "lon": float(top["lon"]),
                    "display_name": top.get("display_name"),
                    "class": top.get("class"),
                    "type": top.get("type"),
                    "importance": top.get("importance"),
                    "boundingbox": top.get("boundingbox"),  # Useful for API responses
                }
            # If no results, try next query variation
            time.sleep(0.5)  # Small delay between attempts
        except RuntimeError:
            # If rate limited or blocked, try without country filter
            if countrycodes:
                try:
                    results = nominatim_geocode(query, limit=3, email=email, countrycodes=None)
                    if results and len(results) > 0:
                        top = results[0]
                        return {
                            "input": query,
                            "lat": float(top["lat"]),
                            "lon": float(top["lon"]),
                            "display_name": top.get("display_name"),
                            "class": top.get("class"),
                            "type": top.get("type"),
                            "importance": top.get("importance"),
                            "boundingbox": top.get("boundingbox"),
                        }
                except RuntimeError:
                    continue
            continue
    
    return None


# Backward compatibility alias
def geocode_first_line(first_line: str, outcode: str = "M3", city: str = "Manchester", email: Optional[str] = None) -> Optional[Dict[str, Any]]:
    """
    Legacy function for backward compatibility.
    Use geocode_address() for new code.
    """
    return geocode_address(first_line, city=city, email=email)
