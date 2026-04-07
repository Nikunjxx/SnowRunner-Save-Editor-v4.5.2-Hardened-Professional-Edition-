# [PH3-IDM-001] ID Normalization Layer
from typing import Dict, Optional

class IDMapper:
    """
    Mandatory translation layer between Raw Save IDs and Registry Canonical Names.
    Ensures identity-based resolution across the interpretation engine and MapRunner.
    """
    
    # [PH3-IDM-002] Static Mapping Registry
    # This should be updated as more vehicles and regions are added to the registry.
    RAW_TO_CANONICAL = {
        # Trucks
        "ws_4964_white": "western_star_4964",
        "chevrolet_ck1500": "chevrolet_ck1500",
        "fleetstar_f2070a": "fleetstar_f2070a",
        "gmc_mh9500": "gmc_mh9500",
        "internation_paystar_5000": "paystar_5000",
        "khan_39_marshall": "khan_39_marshall",
        "krs_58_bandit": "bandit",
        "tuz_420_tartarin": "tartarin",
        
        # Upgrades (Examples)
        "upgrade_us_scout_chevrolet_ck1500_suspension_high": "ck1500_raised_suspension",
        "upgrade_us_truck_fleetstar_f2070a_suspension_high": "f2070a_raised_suspension"
    }
    
    # [PH3-IDM-003] Reverse Mapping for UI -> Save Logic
    CANONICAL_TO_RAW = {v: k for k, v in RAW_TO_CANONICAL.items()}

    @classmethod
    def resolve(cls, raw_id: str) -> str:
        """Translates a raw save string into a canonical MapRunner identifier."""
        if not raw_id:
            return ""
        return cls.RAW_TO_CANONICAL.get(raw_id, raw_id)

    @classmethod
    def get_raw(cls, canonical_id: str) -> str:
        """Translates a canonical identifier back into a raw save string (for mutation)."""
        return cls.CANONICAL_TO_RAW.get(canonical_id, canonical_id)
