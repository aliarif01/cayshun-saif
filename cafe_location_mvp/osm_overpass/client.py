from __future__ import annotations
import json
import os
import time
from typing import Any, Dict, Optional

import requests
from tenacity import retry, stop_after_attempt, wait_exponential_jitter, retry_if_exception_type

from .utils import ensure_debug_dir, short_id, timestamp

class OverpassError(Exception):
    pass

def _env_int(name: str, default: int) -> int:
    try:
        return int(os.getenv(name, str(default)))
    except ValueError:
        return default

def _debug_enabled() -> bool:
    return os.getenv("DEBUG_OVERPASS", "0") == "1"

@retry(
    stop=stop_after_attempt(_env_int("OVERPASS_MAX_RETRIES", 3)),
    wait=wait_exponential_jitter(initial=1.0, max=10.0),
    retry=retry_if_exception_type((requests.RequestException, OverpassError)),
    reraise=True,
)
def run_overpass_query(query: str, timeout_seconds: Optional[int] = None) -> Dict[str, Any]:
    url = os.getenv("OVERPASS_URL", "https://overpass-api.de/api/interpreter")
    # Use provided timeout, or env var, or default to 90 seconds (matching query timeout)
    if timeout_seconds is None:
        timeout_s = _env_int("OVERPASS_TIMEOUT_SECONDS", 90)
    else:
        timeout_s = timeout_seconds
    # Add buffer: HTTP timeout should be longer than Overpass query timeout
    # Overpass query timeout is in the query itself, HTTP timeout should be query_timeout + buffer
    http_timeout = timeout_s + 30  # Add 30 second buffer for network overhead
    debug = _debug_enabled()

    req_id = short_id(query + timestamp())
    dbg_dir = ensure_debug_dir() if debug else None

    if debug and dbg_dir:
        (dbg_dir / f"{req_id}.ql").write_text(query, encoding="utf-8")

    t0 = time.time()
    try:
        resp = requests.post(url, data={"data": query}, timeout=http_timeout)
    except requests.Timeout as e:
        error_msg = f"HTTP request timed out after {http_timeout}s (query timeout: {timeout_s}s)"
        if debug:
            print(f"[overpass:{req_id}] {error_msg}")
        raise OverpassError(error_msg) from e
    except requests.RequestException as e:
        error_msg = f"Network error: {e}"
        if debug:
            print(f"[overpass:{req_id}] {error_msg}")
        raise OverpassError(error_msg) from e

    elapsed_ms = int((time.time() - t0) * 1000)
    text = resp.text

    if debug and dbg_dir:
        (dbg_dir / f"{req_id}.raw.txt").write_text(text, encoding="utf-8")
        print(f"[overpass:{req_id}] status={resp.status_code} time={elapsed_ms}ms bytes={len(text)}")

    # Handle retryable HTTP errors
    if resp.status_code in (429, 502, 503, 504):
        raise OverpassError(f"Retryable Overpass HTTP {resp.status_code}")

    if not resp.ok:
        snippet = text[:800].replace("\n", " ")
        raise OverpassError(f"Overpass HTTP {resp.status_code}: {snippet}")

    # Parse JSON
    try:
        data = json.loads(text)
    except json.JSONDecodeError as e:
        raise OverpassError(f"Invalid JSON from Overpass: {e}")

    # Basic sanity checks
    elements = data.get("elements", [])
    if debug:
        print(f"[overpass:{req_id}] elements={len(elements)}")

    if debug and dbg_dir:
        (dbg_dir / f"{req_id}.json").write_text(json.dumps(data, indent=2), encoding="utf-8")

    return data
