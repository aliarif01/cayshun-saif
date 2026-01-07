from __future__ import annotations

from typing import Dict, List, Literal
from pydantic import BaseModel, Field

# "*" means "tag exists", not a specific value
class TagFilter(BaseModel):
    key: str
    values: List[str] = Field(default_factory=list)

class RadiusArea(BaseModel):
    mode: Literal["radius"] = "radius"
    lat: float
    lon: float
    radius_m: int

class BBoxArea(BaseModel):
    mode: Literal["bbox"] = "bbox"
    south: float
    west: float
    north: float
    east: float

Area = RadiusArea | BBoxArea

# This module must define OSM_LAYERS at import-time (top-level),
# not inside any function.
OSM_LAYERS: Dict[str, List[TagFilter]] = {
    # A) Competition
    "competition": [
        TagFilter(key="amenity", values=["cafe"]),
        TagFilter(key="shop", values=["coffee"]),
    ],

    # C2) Public transport accessibility (comprehensive transit objects)
    "public_transport_accessibility": [
        # Bus infrastructure
        TagFilter(key="public_transport", values=["platform", "stop_position"]),
        TagFilter(key="highway", values=["bus_stop"]),
        TagFilter(key="amenity", values=["bus_station"]),
        
        # Rail infrastructure
        TagFilter(key="railway", values=["station", "halt", "tram_stop", "subway_entrance"]),
        TagFilter(key="railway", values=["platform"]),  # Railway platforms
        TagFilter(key="public_transport", values=["station"]),  # General PT stations
        
        # Metro/Underground
        TagFilter(key="subway_entrance", values=["yes"]),
        TagFilter(key="railway", values=["subway"]),  # Subway lines/stations
        
        # Light rail and trams
        TagFilter(key="light_rail", values=["station"]),
        TagFilter(key="railway", values=["light_rail"]),
        
        # Ferry terminals
        TagFilter(key="amenity", values=["ferry_terminal"]),
        TagFilter(key="public_transport", values=["ferry_terminal"]),
        
        # Taxi ranks
        TagFilter(key="amenity", values=["taxi"]),
        
        # Bike sharing stations
        TagFilter(key="amenity", values=["bicycle_rental"]),
    ],

    # B) Footfall proxies (walkability + crossings + transit)
    "footfall": [
        TagFilter(key="highway", values=["footway", "pedestrian", "path", "steps"]),
        TagFilter(key="highway", values=["crossing"]),
        TagFilter(key="public_transport", values=["platform", "stop_position"]),
        TagFilter(key="highway", values=["bus_stop"]),
        TagFilter(key="railway", values=["station", "tram_stop"]),
        TagFilter(key="subway_entrance", values=["yes"]),
        TagFilter(key="amenity", values=["bicycle_parking"]),
    ],

    # C) Demand drivers / context
    "demand_drivers": [
        TagFilter(key="building", values=["office", "commercial", "apartments"]),
        TagFilter(key="office", values=["*"]),  # tag exists
        TagFilter(key="amenity", values=["school", "university", "college"]),
        TagFilter(key="landuse", values=["commercial", "retail", "residential"]),
        TagFilter(key="shop", values=["supermarket", "convenience", "mall", "bakery"]),
    ],

    # D) Property/cost proxies (proxies only)
    "property_cost_proxies": [
        TagFilter(key="building", values=["retail", "commercial"]),
        TagFilter(key="shop", values=["vacant"]),
        TagFilter(key="disused:shop", values=["*"]),
        TagFilter(key="construction", values=["retail", "commercial"]),
        TagFilter(key="highway", values=["primary", "secondary", "tertiary"]),
    ],
}

USEFUL_TAGS = [
    "name",
    "brand",
    "operator",
    "opening_hours",
    "addr:housenumber",
    "addr:street",
    "addr:postcode",
]
