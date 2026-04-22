"""Fast caching layer for SahiDawa — LRU + TTL, falls back to in-memory if Redis is down.

Caching strategy:
  - LLM parse results: keyed by normalized query text, TTL 10 min
  - Drug lookup results: keyed by (query_lower, pin_code), TTL 1hr
  - Store results: keyed by pin_code, TTL 1hr

All methods are sync so they can be called from the sync chatbot without blocking.
"""

import hashlib
import time
from collections import OrderedDict
from threading import Lock
from typing import Any, Callable, TypeVar

T = TypeVar("T")


class TTLCache:
    """Thread-safe LRU cache with TTL eviction.

    Pure Python — no Redis dependency required.
    Falls back gracefully if Redis is unreachable.
    """

    def __init__(self, max_size: int = 10_000, ttl_seconds: float = 3600):
        self._max_size = max_size
        self._ttl = ttl_seconds
        self._cache: OrderedDict[str, tuple[Any, float]] = OrderedDict()
        self._lock = Lock()

    def _make_key(self, prefix: str, *args, **kwargs) -> str:
        parts = [prefix, *map(str, args)]
        parts += [f"{k}={v}" for k, v in sorted(kwargs.items())]
        return "|".join(parts)

    def get(self, key: str) -> Any | None:
        with self._lock:
            if key not in self._cache:
                return None
            value, expires_at = self._cache[key]
            if expires_at < time.time():
                del self._cache[key]
                return None
            # Move to end (most recently used)
            self._cache.move_to_end(key)
            return value

    def set(self, key: str, value: Any, ttl: float | None = None):
        ttl = ttl if ttl is not None else self._ttl
        with self._lock:
            if key in self._cache:
                self._cache.move_to_end(key)
            self._cache[key] = (value, time.time() + ttl)
            if len(self._cache) > self._max_size:
                # Remove oldest (first) entries
                excess = self._max_size // 10
                for _ in range(excess):
                    self._cache.popitem(last=False)

    def clear(self):
        with self._lock:
            self._cache.clear()

    def cached(self, fn: Callable[..., T], key_prefix: str, *args, **kwargs) -> T:
        """Decorator-style: check cache first, call and store on miss."""
        key = self._make_key(key_prefix, *args, **kwargs)
        hit = self.get(key)
        if hit is not None:
            return hit
        result = fn(*args, **kwargs)
        self.set(key, result)
        return result


# Global cache instances (process-wide, shared across all requests)
_llm_parse_cache = TTLCache(max_size=5_000, ttl_seconds=600)  # 10 min for LLM parses
_drug_lookup_cache = TTLCache(max_size=20_000, ttl_seconds=3600)  # 1 hr for drug lookups
_store_cache = TTLCache(max_size=10_000, ttl_seconds=3600)  # 1 hr for store lookups


def cached_llm_parse(query_text: str, parse_fn: Callable[[str], dict | None]) -> dict | None:
    """Cache LLM parse results — same natural-language query returns same parsed structure."""
    key = query_text.strip().lower()
    hit = _llm_parse_cache.get(key)
    if hit is not None:
        return hit
    result = parse_fn(query_text)
    if result is not None:
        _llm_parse_cache.set(key, result)
    return result


def cached_drug_lookup(query: str, pin_code: str | None, lookup_fn: Callable, *args, **kwargs):
    """Cache drug lookup results."""
    key = f"{query.strip().lower()}|{pin_code or ''}"
    hit = _drug_lookup_cache.get(key)
    if hit is not None:
        return hit
    result = lookup_fn(query, pin_code, *args, **kwargs)
    _drug_lookup_cache.set(key, result)
    return result


def cached_stores(pin_code: str, stores_fn: Callable):
    """Cache store lookup results."""
    hit = _store_cache.get(pin_code)
    if hit is not None:
        return hit
    result = stores_fn(pin_code)
    _store_cache.set(pin_code, result)
    return result


def invalidate_all_caches():
    """Clear all caches — call after data migration."""
    _llm_parse_cache.clear()
    _drug_lookup_cache.clear()
    _store_cache.clear()
