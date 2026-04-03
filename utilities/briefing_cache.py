"""
Caching layer for briefing data to optimize repeated loads.

Briefing data is static (UiPath skill content, patterns, templates) and loaded
multiple times throughout the pipeline. This cache reduces I/O by loading once
and reusing across all agents.
"""

import json
import hashlib
from typing import Dict, Any, Optional
from pathlib import Path
import time


class BriefingCache:
    """Simple in-memory cache for briefing data with optional persistence."""
    
    def __init__(self, enable_persistence: bool = False, cache_dir: str = ".cache"):
        """
        Initialize briefing cache.
        
        Args:
            enable_persistence: Save cache to disk for cross-session reuse
            cache_dir: Directory for persistent cache files
        """
        self._cache: Dict[str, Dict[str, Any]] = {}
        self._timestamps: Dict[str, float] = {}
        self._enable_persistence = enable_persistence
        self._cache_dir = Path(cache_dir)
        
        if enable_persistence:
            self._cache_dir.mkdir(exist_ok=True)
    
    def get(self, key: str) -> Optional[Dict[str, Any]]:
        """
        Retrieve cached briefing data.
        
        Args:
            key: Cache key (e.g., "requirements_briefing", "design_briefing")
            
        Returns:
            Cached data or None if not in cache
        """
        if key in self._cache:
            return self._cache[key]
        
        # Try disk cache if enabled
        if self._enable_persistence:
            return self._load_from_disk(key)
        
        return None
    
    def set(self, key: str, value: Dict[str, Any]) -> None:
        """
        Store briefing data in cache.
        
        Args:
            key: Cache key
            value: Data to cache
        """
        self._cache[key] = value
        self._timestamps[key] = time.time()
        
        if self._enable_persistence:
            self._save_to_disk(key, value)
    
    def clear(self) -> None:
        """Clear all cached data."""
        self._cache.clear()
        self._timestamps.clear()
    
    def stats(self) -> Dict[str, Any]:
        """Return cache statistics."""
        return {
            "cached_keys": list(self._cache.keys()),
            "cache_size": len(self._cache),
            "timestamps": self._timestamps
        }
    
    def _load_from_disk(self, key: str) -> Optional[Dict[str, Any]]:
        """Load cached data from disk if available."""
        cache_file = self._cache_dir / f"{key}.json"
        if cache_file.exists():
            try:
                with open(cache_file, "r") as f:
                    data = json.load(f)
                    self._cache[key] = data
                    return data
            except (json.JSONDecodeError, IOError):
                return None
        return None
    
    def _save_to_disk(self, key: str, value: Dict[str, Any]) -> None:
        """Save cached data to disk."""
        cache_file = self._cache_dir / f"{key}.json"
        try:
            with open(cache_file, "w") as f:
                json.dump(value, f, indent=2)
        except IOError:
            pass  # Silently fail; in-memory cache still works


# Global cache instance
_briefing_cache = BriefingCache(enable_persistence=False)


def get_briefing_cache() -> BriefingCache:
    """Get the global briefing cache instance."""
    return _briefing_cache


def cache_briefing(cache_key: str):
    """
    Decorator for briefing agent functions.
    
    Usage:
        @cache_briefing("requirements_briefing")
        async def requirements_briefing_agent(state):
            # Function body
            ...
    """
    def decorator(func):
        async def wrapper(state):
            cache = get_briefing_cache()
            
            # Check cache first
            cached = cache.get(cache_key)
            if cached:
                # Return state update with cached briefing
                briefing_key = cache_key.replace("_briefing", "")
                return {
                    "briefings": {
                        **state.briefings,
                        briefing_key: cached
                    }
                }
            
            # Not cached; execute function
            result = await func(state)
            
            # Cache the briefing data
            if result and "briefings" in result:
                briefing_data = result["briefings"].get(briefing_key)
                if briefing_data:
                    cache.set(cache_key, briefing_data)
            
            return result
        
        return wrapper
    return decorator
