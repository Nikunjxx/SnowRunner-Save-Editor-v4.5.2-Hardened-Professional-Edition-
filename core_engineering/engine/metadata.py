import os
import json
from typing import Any, Dict, Optional

class MetadataDetector:
    """
    Heuristic-driven Game Build Detection.
    Evolves with the SnowRunner platform to ensure backward compatibility.
    """
    
    @staticmethod
    def detect_game_build(save_data: Dict[str, Any]) -> str:
        """
        Detects game version based on specific key signatures.
        """
        # Baseline check (Season 1 had fewer keys in SslValue)
        ssl = save_data.get("SslValue", {})
        
        if "customTrialData" in ssl:
            return "SEASON_10+" # Rough heuristic
        elif "modInventory" in save_data:
            return "SEASON_5+"
        
        return "LEGACY_OR_BASE"

    @staticmethod
    def get_tool_metadata() -> Dict[str, str]:
        return {
            "tool_version": "1.10.0-SUPREME",
            "engine_status": "HARDENED",
            "author": "Antigravity Engineering"
        }
