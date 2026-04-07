import os
import json
from typing import List, Dict, Any

class ScenarioAction:
    def __init__(self, feature: str, region: str = "GLOBAL", value: Any = None, xp_value: Any = None, 
                 objective_id: str = None, achievement_id: str = None, supplemental_data: Dict[str, Any] = None):
        self.feature = feature
        self.region = region
        self.value = value
        self.xp_value = xp_value
        self.objective_id = objective_id
        self.achievement_id = achievement_id
        self.supplemental_data = supplemental_data

class Scenario:
    def __init__(self, id: str, name: str, description: str, actions: List[Dict[str, Any]]):
        self.id = id
        self.name = name
        self.description = description
        self.actions = [ScenarioAction(**a) for a in actions]

class ScenarioEngine:
    """
    Loads and manages the 'Preset Registry' of complex multi-step workflows.
    v110.40+: Supports atomic batch resolution.
    """
    def __init__(self, presets_path: str):
        self.presets_path = presets_path
        self.scenarios = self._load_presets()

    def _load_presets(self) -> Dict[str, Scenario]:
        if not os.path.exists(self.presets_path):
            return self._create_default_presets()
        
        try:
            with open(self.presets_path, 'r') as f:
                data = json.load(f)
                return {s["id"]: Scenario(**s) for s in data}
        except:
            return self._create_default_presets()

    def _create_default_presets(self) -> Dict[str, Scenario]:
        """Golden Scenarios for SnowRunner."""
        presets = [
            {
                "id": "EXPLORER_MODE",
                "name": "Explorer Mode",
                "description": "Unlocks all maps, reveals all upgrades, unlocks all watchtowers, and discovers hidden trucks globally.",
                "actions": [
                    {"feature": "unlock_maps", "region": "GLOBAL"},
                    {"feature": "reveal_upgrades", "region": "GLOBAL"},
                    {"feature": "unlock_watchtowers", "region": "GLOBAL"},
                    {"feature": "discover_trucks", "region": "GLOBAL"}
                ]
            },
            {
                "id": "LOGISTICS_MASTER",
                "name": "Logistics Master",
                "description": "Repairs and refuels all vehicles and trailers globally.",
                "actions": [
                    {"feature": "repair_vehicle", "region": "GLOBAL"},
                    {"feature": "repair_trailer", "region": "GLOBAL"}
                ]
            },
            {
                "id": "RECOVERY_MODE",
                "name": "Recovery Mode",
                "description": "Fixes broken recovery and resets all tasks for the current region.",
                "actions": [
                    {"feature": "fix_recovery", "region": "GLOBAL"}
                ]
            }
        ]
        
        # Save defaults
        try:
            os.makedirs(os.path.dirname(self.presets_path), exist_ok=True)
            with open(self.presets_path, 'w') as f:
                json.dump([{"id": s["id"], "name": s["name"], "description": s["description"], 
                            "actions": [vars(a) for a in s.actions]} for s in [Scenario(**p) for p in presets]], f, indent=4)
        except: pass

        return {s["id"]: Scenario(**s) for s in presets}

    def get_scenario(self, scenario_id: str) -> Scenario:
        return self.scenarios.get(scenario_id)

    def list_scenarios(self) -> List[Dict[str, str]]:
        return [{"id": s.id, "name": s.name, "description": s.description} for s in self.scenarios.values()]
