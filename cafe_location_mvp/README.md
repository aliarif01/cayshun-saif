# Cafe Location Optimizer - Overpass API Integration

This module fetches location data from the Overpass API for cafe location optimization, including competition analysis, footfall indicators, public transport accessibility, and demand drivers.

## Features

- **Geocoding**: Convert addresses/place names to coordinates using Nominatim
- **Location Data Fetching**: Get OSM data for competition, footfall, public transport, and demand drivers
- **API-Ready**: Functions designed for easy integration into web backends

## Installation

1. Install dependencies:
```bash
pip install -r requirements.txt
```

2. (Optional) Create a `.env` file:
```env
# Overpass API settings
OVERPASS_TIMEOUT_SECONDS=90
OVERPASS_MAX_RETRIES=3

# Search radius in meters (default: 900)
SEARCH_RADIUS_M=900

# Geocoding settings
GEOCODE_CITY=Manchester
NOMINATIM_EMAIL=your-email@example.com  # Recommended to avoid 403 errors
```

## Usage

### Command Line

**Using an address/place name:**
```bash
python main.py "Manchester Piccadilly Station"
python main.py "10 Norton Street"
python main.py "Deansgate Manchester"
```

**Using default coordinates:**
```bash
python main.py
```

### As a Python Module (for Backend Integration)

```python
from main import fetch_location_data
from osm_overpass.geocoder import geocode_address

# Geocode an address
geocode_result = geocode_address("Manchester Piccadilly Station")
if geocode_result:
    lat = geocode_result["lat"]
    lon = geocode_result["lon"]
    
    # Fetch location data
    results = fetch_location_data(
        lat=lat,
        lon=lon,
        radius_m=900,
        layers=["competition", "footfall", "public_transport_accessibility"]
    )
    
    # Access data by layer
    competition = results["competition"]["elements"]
    footfall = results["footfall"]["elements"]
```

### Web API Example

See `api_example.py` for a complete Flask API example. To use it:

1. Install Flask:
```bash
pip install flask
```

2. Run the API:
```bash
python api_example.py
```

3. Make requests:
```bash
# Geocode an address
curl "http://localhost:5000/api/geocode?address=Manchester%20Piccadilly%20Station"

# Get location data by address
curl "http://localhost:5000/api/location-data?address=Manchester%20Piccadilly%20Station&radius_m=900"

# Get location data by coordinates
curl "http://localhost:5000/api/location-data?lat=53.4775&lon=-2.2315&radius_m=900"
```

## Data Layers

The code fetches the following data layers:

- **competition**: Cafes and coffee shops
- **footfall**: Footways, crossings, pedestrian areas, bicycle parking
- **public_transport_accessibility**: Bus stops, train stations, tram stops, subway entrances
- **demand_drivers**: Offices, schools, universities, commercial buildings, shops

## API Functions

### `geocode_address(address, city=None, country="UK", email=None)`

Geocode an address to coordinates. Tries multiple query formats for better results.

**Parameters:**
- `address`: Address or place name (required)
- `city`: Optional city name for context
- `country`: Country name (default: "UK")
- `email`: Optional email for Nominatim (recommended)

**Returns:** Dictionary with `lat`, `lon`, `display_name`, and metadata, or `None` if not found

### `fetch_location_data(lat, lon, radius_m=900, layers=None, timeout_seconds=90)`

Fetch Overpass API data for a location.

**Parameters:**
- `lat`: Latitude (required)
- `lon`: Longitude (required)
- `radius_m`: Search radius in meters (default: 900)
- `layers`: List of layer keys to fetch. If `None`, fetches all layers.
- `timeout_seconds`: Overpass API timeout

**Returns:** Dictionary with layer names as keys and Overpass API responses as values

## Output

Data is saved to `data_raw/` directory as JSON files:
- `competition.json`
- `footfall.json`
- `public_transport_accessibility.json`
- `demand_drivers.json`

Each JSON file contains Overpass API response format with `elements` array.

## Rate Limiting

- **Nominatim**: 1 request per second (automatically handled)
- **Overpass API**: Respects timeout settings, includes retry logic

## Error Handling

- Geocoding failures return `None` or raise `RuntimeError` with details
- Overpass API errors are retried automatically with exponential backoff
- Invalid layer names are skipped silently

## Notes

- Nominatim requires a valid User-Agent (already configured)
- Adding an email to `.env` reduces 403 errors from Nominatim
- Overpass API queries are optimized to avoid heavy geometry data
