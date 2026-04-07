# [PH3-MPR-001] MapRunner Absolute Interface
from typing import Dict, List, Optional, Any
from .engine.registry_loader import RegistryLoader
from .id_mapper import IDMapper
from .models.game_entities import Truck, Upgrade
from core_engineering.utils.resource_utils import resource_path

class MapRunner:
    """
    Layer 1: MapRunner (Game Knowledge Hub)
    High-level interface for identity-based resolution. 
    Strictly isolated from save file structure.
    """
    
    def __init__(self):
        self.loader = RegistryLoader()
        self.id_mapper = IDMapper()

    def get_truck(self, raw_id: str) -> Optional[Truck]:
        """Resolves a raw save ID into a canonical Truck object."""
        canonical_id = self.id_mapper.resolve(raw_id)
        trucks = self.loader.get_registry("trucks")
        
        if canonical_id not in trucks:
            return None
            
        t_data = trucks[canonical_id]
        return Truck(
            id=canonical_id,
            name=t_data.get("name", "Unknown Truck"),
            type=t_data.get("type", "heavy"),
            regions=t_data.get("regions", [])
        )

    def get_upgrades(self, raw_truck_id: str) -> List[Upgrade]:
        """Returns all upgrades supported by a truck identity."""
        canonical_id = self.id_mapper.resolve(raw_truck_id)
        all_upgrades = self.loader.get_registry("upgrades")
        
        truck_upgrades = []
        target_norm = canonical_id.lower().replace(" ", "_").replace("-", "_")
        
        for region, maps in all_upgrades.items():
            for map_name, upgrades in maps.items():
                for upg in upgrades:
                    # Normalized identity cross-referencing
                    reg_norm = upg["vehicle"].lower().replace(" ", "_").replace("-", "_")
                    if reg_norm in target_norm or target_norm in reg_norm:
                        truck_upgrades.append(Upgrade(
                            id=upg["id"],
                            name=upg["name"],
                            vehicle=upg["vehicle"],
                            type=upg["type"],
                            region=region,
                            map=map_name
                        ))
        return truck_upgrades

    def get_regions(self) -> Dict[str, Any]:
        """Returns the regional registry."""
        return self.loader.get_registry("regions")

    def get_contracts(self) -> Dict[str, Any]:
        """Returns the contract registry."""
        return self.loader.get_registry("contracts")
