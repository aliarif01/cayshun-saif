"""
Example API endpoint using Flask/FastAPI to demonstrate how to use
the location data fetching functions in a web backend.

This shows how to integrate the Overpass API code into a web application.
"""

from flask import Flask, jsonify, request
from typing import Optional
import os
from dotenv import load_dotenv

from main import fetch_location_data
from osm_overpass.geocoder import geocode_address

load_dotenv()

app = Flask(__name__)


@app.route('/api/location-data', methods=['GET', 'POST'])
def get_location_data():
    """
    API endpoint to fetch location data.
    
    Query parameters (GET) or JSON body (POST):
    - address: Address/place name to geocode (optional if lat/lon provided)
    - lat: Latitude (optional if address provided)
    - lon: Longitude (optional if address provided)
    - radius_m: Search radius in meters (default: 900)
    - layers: Comma-separated list of layers (default: all)
    
    Returns:
        JSON response with location data
    """
    try:
        # Get parameters from query string (GET) or JSON body (POST)
        if request.method == 'POST':
            data = request.get_json() or {}
        else:
            data = request.args.to_dict()
        
        address = data.get('address')
        lat = data.get('lat', type=float)
        lon = data.get('lon', type=float)
        radius_m = data.get('radius_m', 900, type=int)
        layers_str = data.get('layers')
        
        # Parse layers if provided
        layers = None
        if layers_str:
            layers = [l.strip() for l in layers_str.split(',')]
        
        # Geocode if address provided
        if address:
            city = os.getenv("GEOCODE_CITY", "Manchester")
            email = os.getenv("NOMINATIM_EMAIL")
            
            geocode_result = geocode_address(address, city=city, email=email)
            if not geocode_result:
                return jsonify({
                    "error": "Could not geocode address",
                    "address": address
                }), 400
            
            lat = geocode_result["lat"]
            lon = geocode_result["lon"]
        
        # Validate coordinates
        if lat is None or lon is None:
            return jsonify({
                "error": "Either 'address' or both 'lat' and 'lon' must be provided"
            }), 400
        
        # Fetch location data
        results = fetch_location_data(
            lat=lat,
            lon=lon,
            radius_m=radius_m,
            layers=layers
        )
        
        # Format response
        response = {
            "location": {
                "lat": lat,
                "lon": lon,
                "radius_m": radius_m
            },
            "data": {},
            "summary": {}
        }
        
        for layer, data in results.items():
            elements = data.get("elements", [])
            response["data"][layer] = elements
            response["summary"][layer] = {
                "count": len(elements)
            }
        
        return jsonify(response), 200
        
    except Exception as e:
        return jsonify({
            "error": str(e),
            "type": type(e).__name__
        }), 500


@app.route('/api/geocode', methods=['GET', 'POST'])
def geocode_endpoint():
    """
    API endpoint to geocode an address.
    
    Query parameters (GET) or JSON body (POST):
    - address: Address/place name to geocode (required)
    - city: Optional city name for context
    
    Returns:
        JSON response with geocoded coordinates
    """
    try:
        if request.method == 'POST':
            data = request.get_json() or {}
        else:
            data = request.args.to_dict()
        
        address = data.get('address')
        if not address:
            return jsonify({"error": "Address parameter is required"}), 400
        
        city = data.get('city') or os.getenv("GEOCODE_CITY", "Manchester")
        email = os.getenv("NOMINATIM_EMAIL")
        
        result = geocode_address(address, city=city, email=email)
        
        if not result:
            return jsonify({
                "error": "Could not geocode address",
                "address": address
            }), 404
        
        return jsonify(result), 200
        
    except Exception as e:
        return jsonify({
            "error": str(e),
            "type": type(e).__name__
        }), 500


@app.route('/health', methods=['GET'])
def health():
    """Health check endpoint"""
    return jsonify({"status": "ok"}), 200


if __name__ == '__main__':
    # Run on port 5000 by default
    port = int(os.getenv("PORT", 5000))
    app.run(debug=True, host='0.0.0.0', port=port)
