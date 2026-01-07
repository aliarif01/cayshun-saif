#!/usr/bin/env python3
import argparse
import json
from dataclasses import dataclass
from typing import Dict, Any, List, Tuple, Optional

import numpy as np
import pandas as pd
from sklearn.neighbors import BallTree

EARTH_RADIUS_M = 6371000.0


# --- NaPTAN mode classification (best-effort, robust to variations) ---
# NaPTAN StopType codes vary by extract. We'll:
# 1) map known common codes, then
# 2) fall back to prefix heuristics.
STOPTYPE_TO_MODE = {
    # Bus / Coach
    "BCT": "bus",   # Bus/Coach station
    "BCS": "bus",   # Bus/Coach stop
    "BST": "bus",   # Bus stop
    "BCE": "bus",   # Coach
    "BCQ": "bus",

    # Rail
    "RLY": "rail",
    "RSE": "rail",
    "RPL": "rail",

    # Metro / Underground (varies)
    "MET": "metro",
    "MTR": "metro",
    "UND": "metro",

    # Tram / Light Rail
    "TRM": "tram",
    "LRT": "tram",

    # Ferry
    "FER": "ferry",
    "FTD": "ferry",
}

def mode_from_stoptype(stop_type: Any) -> str:
    if not isinstance(stop_type, str):
        return "other"
    s = stop_type.strip().upper()
    if not s:
        return "other"
    if s in STOPTYPE_TO_MODE:
        return STOPTYPE_TO_MODE[s]

    # Fallback heuristic by leading character(s)
    # (works reasonably even if codes differ)
    if s.startswith("B"):
        return "bus"
    if s.startswith("R"):
        return "rail"
    if s.startswith("M") or "UNDER" in s or "METRO" in s:
        return "metro"
    if s.startswith("T") or "TRAM" in s or "LIGHT" in s:
        return "tram"
    if s.startswith("F") or "FERR" in s:
        return "ferry"
    return "other"


def infer_col(df: pd.DataFrame, candidates: List[str]) -> Optional[str]:
    for c in candidates:
        if c in df.columns:
            return c
    return None


@dataclass
class NaptanIndex:
    tree: BallTree
    df: pd.DataFrame
    lat_col: str
    lon_col: str
    name_col: Optional[str]
    atco_col: Optional[str]
    stoptype_col: Optional[str]


def build_naptan_index(naptan_csv_path: str) -> NaptanIndex:
    df = pd.read_csv(naptan_csv_path, low_memory=False)

    lat_col = infer_col(df, ["Latitude", "latitude", "LATITUDE", "Lat", "lat"])
    lon_col = infer_col(df, ["Longitude", "longitude", "LONGITUDE", "Lon", "lon", "Long", "long"])
    if not lat_col or not lon_col:
        raise ValueError(f"Could not find Latitude/Longitude columns. Found columns: {list(df.columns)[:40]} ...")

    stoptype_col = infer_col(df, ["StopType", "StopTypeCode", "stop_type", "Stop_Type", "StopTypeRef"])
    name_col = infer_col(df, ["CommonName", "commonname", "Name", "StopName", "Landmark", "LocalityName"])
    atco_col = infer_col(df, ["ATCOCode", "AtcoCode", "atcocode", "NaptanCode", "NaPTANCode"])

    # Clean coords
    df = df.dropna(subset=[lat_col, lon_col]).copy()
    df[lat_col] = pd.to_numeric(df[lat_col], errors="coerce")
    df[lon_col] = pd.to_numeric(df[lon_col], errors="coerce")
    df = df.dropna(subset=[lat_col, lon_col]).copy()

    # Add mode column
    if stoptype_col:
        df["_mode"] = df[stoptype_col].apply(mode_from_stoptype)
    else:
        df["_mode"] = "other"

    coords_rad = np.radians(df[[lat_col, lon_col]].to_numpy(dtype=float))
    tree = BallTree(coords_rad, metric="haversine")

    return NaptanIndex(
        tree=tree,
        df=df.reset_index(drop=True),
        lat_col=lat_col,
        lon_col=lon_col,
        name_col=name_col,
        atco_col=atco_col,
        stoptype_col=stoptype_col,
    )


def query_nearby_stops(
    lat: float,
    lon: float,
    idx: NaptanIndex,
    radius_m: float,
) -> pd.DataFrame:
    point_rad = np.radians(np.array([[lat, lon]], dtype=float))
    radius_rad = radius_m / EARTH_RADIUS_M

    ind, dist = idx.tree.query_radius(point_rad, r=radius_rad, return_distance=True)
    ids = ind[0]
    dists_m = dist[0] * EARTH_RADIUS_M

    if len(ids) == 0:
        return pd.DataFrame(columns=["mode", "dist_m"])

    out = idx.df.iloc[ids].copy()
    out["dist_m"] = dists_m
    out = out.rename(columns={"_mode": "mode"})
    out = out.sort_values("dist_m").reset_index(drop=True)
    return out


def stops_to_records(df: pd.DataFrame, idx: NaptanIndex, limit: Optional[int] = None) -> List[Dict[str, Any]]:
    if limit is not None:
        df = df.head(limit)

    records = []
    for _, r in df.iterrows():
        rec = {
            "mode": r.get("mode"),
            "distance_m": float(r.get("dist_m")),
            "lat": float(r.get(idx.lat_col)),
            "lon": float(r.get(idx.lon_col)),
        }
        if idx.stoptype_col and idx.stoptype_col in r:
            rec["stop_type"] = r.get(idx.stoptype_col)
        if idx.name_col and idx.name_col in r:
            rec["name"] = r.get(idx.name_col)
        if idx.atco_col and idx.atco_col in r:
            rec["atco_code"] = r.get(idx.atco_col)
        records.append(rec)
    return records


def nearest_by_mode(df: pd.DataFrame, idx: NaptanIndex) -> Dict[str, Dict[str, Any]]:
    out: Dict[str, Dict[str, Any]] = {}
    if df.empty:
        return out

    for mode, g in df.groupby("mode"):
        r = g.iloc[0]
        out[mode] = {
            "distance_m": float(r["dist_m"]),
            "lat": float(r[idx.lat_col]),
            "lon": float(r[idx.lon_col]),
        }
        if idx.name_col and idx.name_col in r:
            out[mode]["name"] = r.get(idx.name_col)
        if idx.atco_col and idx.atco_col in r:
            out[mode]["atco_code"] = r.get(idx.atco_col)
        if idx.stoptype_col and idx.stoptype_col in r:
            out[mode]["stop_type"] = r.get(idx.stoptype_col)
    return out


def counts_by_mode(df: pd.DataFrame) -> Dict[str, int]:
    if df.empty:
        return {}
    return df["mode"].value_counts().to_dict()


def main():
    ap = argparse.ArgumentParser(description="Find nearby public transport stops (NaPTAN) for properties and output JSON.")
    ap.add_argument("--naptan_csv", required=True, help="Path to NaPTAN stops CSV")
    ap.add_argument("--properties_json", required=True, help="Path to properties JSON (list of {id, lat, lon})")
    ap.add_argument("--radius_m", type=float, default=1609.34, help="Search radius in meters (default 1 mile)")
    ap.add_argument("--include_all_nearby", action="store_true", help="Include a list of nearby stops in output")
    ap.add_argument("--nearby_limit", type=int, default=50, help="Max number of nearby stops to include (if enabled)")
    ap.add_argument("--out_json", default="pt_nearby_output.json", help="Output JSON filename")
    args = ap.parse_args()

    idx = build_naptan_index(args.naptan_csv)

    with open(args.properties_json, "r", encoding="utf-8") as f:
        props = json.load(f)
    if not isinstance(props, list):
        raise ValueError("properties_json must be a JSON list")

    results: List[Dict[str, Any]] = []
    for p in props:
        pid = p.get("id")
        lat = float(p["lat"])
        lon = float(p["lon"])

        nearby_df = query_nearby_stops(lat, lon, idx, args.radius_m)

        item: Dict[str, Any] = {
            "id": pid,
            "lat": lat,
            "lon": lon,
            "radius_m": args.radius_m,
            "counts_by_mode": counts_by_mode(nearby_df),
            "nearest_by_mode": nearest_by_mode(nearby_df, idx),
        }

        if args.include_all_nearby:
            item["nearby_stops"] = stops_to_records(nearby_df, idx, limit=args.nearby_limit)

        results.append(item)

    with open(args.out_json, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)

    print(f"Wrote {len(results)} properties to {args.out_json}")


if __name__ == "__main__":
    main()
