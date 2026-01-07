from __future__ import annotations

import json
import os
import sys
import time
from pathlib import Path
from typing import Optional, List
from dotenv import load_dotenv

from osm_overpass.config import OSM_LAYERS, RadiusArea
from osm_overpass.query_builder import build_overpass_query
from osm_overpass.client import run_overpass_query
from osm_overpass.geocoder import geocode_address


def save_json(path: Path, data: dict):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2), encoding="utf-8")


def fetch_location_data(
    lat: float,
    lon: float,
    radius_m: int = 900,
    layers: Optional[List[str]] = None,
    timeout_seconds: int = 90
) -> dict:
    """
    Fetch Overpass API data for a given location and radius.
    
    This is the main API-friendly function that can be called from a web backend.
    
    Args:
        lat: Latitude
        lon: Longitude
        radius_m: Search radius in meters (default: 900)
        layers: List of layer keys to fetch. If None, fetches all available layers.
        timeout_seconds: Overpass API timeout
        
    Returns:
        Dictionary with layer names as keys and Overpass API responses as values
    """
    area = RadiusArea(lat=lat, lon=lon, radius_m=radius_m)
    
    if layers is None:
        layers = ["competition", "footfall", "public_transport_accessibility", "demand_drivers"]
    
    results = {}
    
    for layer in layers:
        if layer not in OSM_LAYERS:
            continue  # Skip invalid layer names
            
        query = build_overpass_query(
            area=area,
            layers=OSM_LAYERS,
            selected_layer_keys=[layer],
            timeout_seconds=timeout_seconds,
        )
        
        data = run_overpass_query(query)
        results[layer] = data
    
    return results


def main():
    load_dotenv()

    # Check if address/place name provided via command line
    if len(sys.argv) > 1:
        # Geocode the address/place name
        address = " ".join(sys.argv[1:])
        print(f"\n=== Geocoding address: {address} ===")
        
        # Optional: get city and email from env vars
        # Only use city if address doesn't already contain location info
        city = os.getenv("GEOCODE_CITY", "Manchester")
        email = os.getenv("NOMINATIM_EMAIL")  # Optional email for Nominatim
        
        # Detect if address already looks complete (has postcode or location name)
        import re
        has_postcode = bool(re.search(r'\b[A-Z]{1,2}\d{1,2}[A-Z]?\s?\d[A-Z]{2}\b|\b[A-Z]{1,2}\d{1,2}[A-Z]?\b', address.upper()))
        has_location = any(loc in address.lower() for loc in ['london', 'manchester', 'birmingham', 'greater london', 'greater manchester'])
        
        # Don't add city context if address already looks complete
        if has_postcode or has_location or (',' in address and address.count(',') >= 2):
            city = None  # Address is complete, don't add city
        
        try:
            geocode_result = geocode_address(address, city=city, email=email)
        except RuntimeError as e:
            print(f"ERROR: {e}")
            sys.exit(1)
        
        if geocode_result is None:
            print(f"ERROR: Could not geocode '{address}'.")
            print("Tip: Check the address spelling or try a simpler format (e.g., just street name + postcode)")
            print("You can also try searching on https://www.openstreetmap.org to verify the address exists")
            sys.exit(1)
        
        lat = geocode_result["lat"]
        lon = geocode_result["lon"]
        print(f"Found coordinates: lat={lat}, lon={lon}")
        print(f"Location: {geocode_result.get('display_name', 'N/A')}")
        
        # Respect Nominatim rate limits (1 req/sec)
        time.sleep(1.1)
    else:
        # Use hardcoded coordinates (default behavior)
        lat = 53.4794
        lon = -2.2453
        print(f"Using default coordinates: lat={lat}, lon={lon}")

    # Get radius and timeout from env or use defaults
    radius_m = int(os.getenv("SEARCH_RADIUS_M", "900"))
    timeout_s = int(os.getenv("OVERPASS_TIMEOUT_SECONDS", "90"))

    # Fetch all location data using the API-friendly function
    print(f"\n=== Fetching Overpass data (radius: {radius_m}m) ===")
    results = fetch_location_data(
        lat=lat,
        lon=lon,
        radius_m=radius_m,
        timeout_seconds=timeout_s
    )

    # Save results to JSON files
    out_dir = Path("data_raw")
    for layer, data in results.items():
        save_json(out_dir / f"{layer}.json", data)
        element_count = len(data.get("elements", []))
        print(f"Saved: {out_dir / f'{layer}.json'}  elements={element_count}")
        
        # Special message for public transport
        if layer == "public_transport_accessibility":
            print(f"  → Public transport accessibility data saved with {element_count} stops/stations within {radius_m}m radius")

    # Print summary
    total = sum(len(results[k].get("elements", [])) for k in results.keys())
    print("\nDone. Total elements across layers:", total)
    
    # Verify public transport was collected
    if "public_transport_accessibility" in results:
        pt_count = len(results["public_transport_accessibility"].get("elements", []))
        print(f"✓ Public transport: {pt_count} stops/stations found within {radius_m}m radius")


if __name__ == "__main__":
    main()