from __future__ import annotations
import hashlib
import os
from pathlib import Path
from datetime import datetime

def ensure_debug_dir() -> Path:
    d = Path(os.getcwd()) / "debug_overpass"
    d.mkdir(parents=True, exist_ok=True)
    return d

def short_id(text: str) -> str:
    return hashlib.sha1(text.encode("utf-8")).hexdigest()[:10]

def timestamp() -> str:
    return datetime.utcnow().strftime("%Y%m%d_%H%M%S")
