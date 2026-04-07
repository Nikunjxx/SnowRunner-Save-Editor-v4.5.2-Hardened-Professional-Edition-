# [PH3-MAP-002] SnowRunner Field Mapper Engine
import yaml
import os
from typing import Dict, Any, List
from core_engineering.engine.fast_cache import cache
from core_engineering.utils.resource_utils import resource_path

class FieldMapper:
    """
    Layer 2: The Bridge (Interpretation Engine <-> MapRunner).
    Resolves the interpreted game state into a high-level UI model.
    """
    
    REGISTRY_PATH = resource_path("core_engineering/mapper/field_registry.yaml")
    
    def __init__(self, maprunner):
        self.maprunner = maprunner
        with open(self.REGISTRY_PATH, 'r') as f:
            self.registry = yaml.safe_load(f)["fields"]

    def resolve(self, interpreted_state: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        """
        [PH4-PERF-004] Cached Resolution Pipeline.
        Resolves UI model from engine truth, ensuring zero-redundancy.
        """
        # [STEP 1] Check Cache
        cache_key = f"resolved_model_{id(interpreted_state)}"
        cached_result = cache.get(cache_key)
        if cached_result:
             return cached_result
             
        # [STEP 2] Absolute Resolution
        ui_model = {
            "player": self._resolve_player(interpreted_state),
            "trucks": self._resolve_trucks(interpreted_state),
            "upgrades": self._resolve_upgrades(interpreted_state)
        }
        
        # [STEP 3] Store in Cache
        cache.set(cache_key, ui_model)
        
        return ui_model

    def resolve_ui_state(self, interpreted_state: Dict[str, Any]) -> Dict[str, Any]:
        """Legacy alias for backward compatibility."""
        return self.resolve(interpreted_state, {})

    def _resolve_player(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """Maps Player Stats from interpreted derived state."""
        return {
            "money": state.get("derived.player.money", 0),
            "rank": state.get("derived.player.rank", 1),
            "experience": state.get("derived.player.experience", 0)
        }

    def _resolve_trucks(self, state: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Maps Trucks from Warehouse using ID normalization (IDMapper).
        This resolves index-based warehouse lists into identity-based entities.
        """
        # Source path from registry
        raw_trucks = state.get("CompleteSave.SslValue.persistentProfileData.trucksInWarehouse", [])
        resolved_trucks = []
        
        for truck_data in raw_trucks:
            # IDENTITY RESOLUTION
            raw_id = truck_data.get("type", "unknown")
            canonical_truck = self.maprunner.get_truck(raw_id)
            
            if canonical_truck:
                resolved_trucks.append({
                    "id": canonical_truck.id,
                    "name": canonical_truck.name,
                    "type": canonical_truck.type,
                    "is_unlocked": truck_data.get("isUnlocked", True)
                })
        return resolved_trucks

    def _resolve_upgrades(self, state: Dict[str, Any]) -> Dict[str, List[Dict[str, Any]]]:
        """
        Dynamic Resolver for Upgrades.
        This provides context-aware information directly from MapRunner Knowledge.
        """
        # Example: Placeholder for when we have a selected truck Context
        return {}
