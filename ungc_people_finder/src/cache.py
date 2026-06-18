import json
import hashlib
import time
import logging
from pathlib import Path
from typing import Optional, Any

logger = logging.getLogger("ungc.cache")

CACHE_DIR = Path(__file__).parent.parent / "data" / "cache"

def _key(text: str) -> str:
    return hashlib.sha256(text.encode()).hexdigest()

def _path(key: str) -> Path:
    return CACHE_DIR / f"{key}.json"

def get(query: str, ttl_hours: int = 24) -> Optional[Any]:
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    p = _path(_key(query))
    if not p.exists():
        return None
    data = json.loads(p.read_text())
    age = time.time() - data.get("ts", 0)
    if age > ttl_hours * 3600:
        p.unlink(missing_ok=True)
        return None
    logger.debug(f"Cache hit: {query[:60]}")
    return data.get("value")

def set(query: str, value: Any) -> None:
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    p = _path(_key(query))
    p.write_text(json.dumps({"ts": time.time(), "value": value}))

def clear() -> int:
    count = 0
    for f in CACHE_DIR.glob("*.json"):
        f.unlink()
        count += 1
    return count
