# [PH3-REG-001] MapRunner Registry Loader
import yaml
import os
from typing import Dict, Any
from core_engineering.utils.resource_utils import resource_path

class RegistryLoader:
    """
    Lazy-loading engine for MapRunner YAML registries.
    Ensures that game data is only loaded into memory when requested by the UI panels.
    """
    
    REGISTRY_DIR = resource_path("core_engineering/maprunner/registry")
    
    def __init__(self):
        self._cache: Dict[str, Dict[str, Any]] = {}

    def get_registry(self, name: str) -> Dict[str, Any]:
        """Loads a YAML registry by name (e.g., 'trucks', 'upgrades') with caching."""
        if name in self._cache:
            return self._cache[name]
        
        file_path = os.path.join(self.REGISTRY_DIR, f"{name}.yaml")
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"MapRunner Registry '{name}' not found at {file_path}")
            
        with open(file_path, 'r') as f:
            data = yaml.safe_load(f)
            self._cache[name] = data
            return data

    def clear_cache(self):
        """Standard cache reset logic."""
        self._cache.clear()
