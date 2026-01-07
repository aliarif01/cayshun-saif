from __future__ import annotations

from typing import Dict, List
from .config import Area, TagFilter


def _area_selector(area: Area) -> str:
    if area.mode == "radius":
        return f"(around:{area.radius_m},{area.lat},{area.lon})"
    return f"({area.south},{area.west},{area.north},{area.east})"


def _filter_to_ql(f: TagFilter) -> List[str]:
    if "*" in f.values:
        return [f'["{f.key}"]']
    return [f'["{f.key}"="{v}"]' for v in f.values]


def build_overpass_query(
    area: Area,
    layers: Dict[str, List[TagFilter]],
    selected_layer_keys: List[str],
    timeout_seconds: int = 90,
) -> str:
    sel = _area_selector(area)

    lines: List[str] = []
    for layer_key in selected_layer_keys:
        filters = layers.get(layer_key, [])
        for f in filters:
            for ql in _filter_to_ql(f):
                # Keep it light: nodes + ways + relations but only return center (not full geometry)
                lines.append(f"node{ql}{sel};")
                lines.append(f"way{ql}{sel};")
                lines.append(f"relation{ql}{sel};")

    # IMPORTANT: no recursion (">; out skel") — this is what was making it heavy
    query = f"""
[out:json][timeout:{timeout_seconds}];
(
  {'\n  '.join(lines)}
);
out tags center qt;
""".strip()

    return query
