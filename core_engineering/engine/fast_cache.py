# [PH4-PERF-004] Atomic Resolution Cache (HARDENED)
import time
from typing import Any, Dict, Optional

class FastCache:
    """
    State-Aware Resolution Cache.
    Ensures that expensive interpretation cycles are reused across lazy UI events,
    while providing absolute safety via global invalidation.
    """
    
    def __init__(self, ttl_seconds: float = 60.0):
        self._store: Dict[str, Any] = {}
        self._timestamps: Dict[str, float] = {}
        self._ttl = ttl_seconds

    def get(self, key: str) -> Optional[Any]:
        """Retrieves a cached value if it exists and is fresh."""
        if key in self._store:
            # Check for TTL expiry [OPTIONAL PROTECTION]
            if time.time() - self._timestamps[key] < self._ttl:
                 return self._store[key]
            else:
                 self.invalidate(key)
        return None

    def set(self, key: str, value: Any):
        """Caches a value with a fresh timestamp."""
        self._store[key] = value
        self._timestamps[key] = time.time()

    def invalidate(self, key: str):
        """Specific key removal."""
        self._store.pop(key, None)
        self._timestamps.pop(key, None)

    def invalidate_all(self):
        """
        [PH4-SAFE-INV] Global Hard Invalidation.
        Must be triggered on mutation, rollback, or load events.
        """
        self._store.clear()
        self._timestamps.clear()
        print("PERF: Global Cache Invalidation Complete.")

# Central Singleton for the core_engineering package
cache = FastCache()
