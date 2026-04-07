import os
import json
from typing import List, Dict, Any, Tuple

class SecurityError(Exception):
    """Raised when a mutation attempt violates security boundaries."""
    pass

class DependencyResolver:
    """
    Ensures that partial updates (e.g. Reveal Map) execute with all 
    MANDATORY global dependencies registered, without 'improving' 
    unrelated progression.
    """
    
    METADATA_VERSION = "v1.1"
    
    # [v110.41] Objective Metadata Registry
    # Classifies objectives to ensure 100% accurate world-state marker (STS) linkage.
    OBJECTIVE_METADATA = {
        # Michigan (Black River)
        "US_01_01_ROCKFALL_OB":     {"region_name": "Michigan", "affects_world": True, "map": "us_01_01", "marker_id": "US_01_01_ROCKFALL_OB_MARKER", "rewards": {"money": 1500, "xp": 120}},
        "US_01_01_BRIDGE_REPAIR":   {"region_name": "Michigan", "affects_world": True, "map": "us_01_01", "marker_id": "US_01_01_BRIDGE_REPAIR", "rewards": {"money": 2100, "xp": 250}},
        "US_01_01_WOODEN_BRIDGE":   {"region_name": "Michigan", "affects_world": True, "map": "us_01_01", "marker_id": "US_01_01_WOODEN_BRIDGE", "rewards": {"money": 1800, "xp": 180}},
        
        # Michigan (Smithville Dam)
        "US_01_02_ROCKFALL_MAIN":   {"region_name": "Michigan", "affects_world": True, "map": "us_01_02", "marker_id": "US_01_02_ROCKFALL_MAIN", "rewards": {"money": 3200, "xp": 350}},
        
        # Taymyr (Drowned Lands)
        "RU_02_01_BRIDGE_MAIN":     {"region_name": "Taymyr", "affects_world": True, "map": "ru_02_01", "marker_id": "RU_02_01_BRIDGE_MAIN", "rewards": {"money": 5400, "xp": 600}},
        "RU_02_01_ROAD_CLEAR":      {"region_name": "Taymyr", "affects_world": True, "map": "ru_02_01", "marker_id": "RU_02_01_ROAD_CLEAR", "rewards": {"money": 4200, "xp": 450}},
        
        # Alaska
        "US_02_01_PIPELINE_FIX":    {"region_name": "Alaska", "affects_world": True, "map": "us_02_01", "marker_id": "US_02_01_PIPELINE_FIX", "rewards": {"money": 8200, "xp": 950}},
    }

    # [v110.50] Region to Level ID Mapping
    REGION_LEVELS = {
        "Michigan": ["level_us_01_01", "level_us_01_02", "level_us_01_03", "level_us_01_04"],
        "Alaska": ["level_us_02_01", "level_us_02_02", "level_us_02_03", "level_us_02_04"],
        "Taymyr": ["level_ru_02_01", "level_ru_02_02", "level_ru_02_03", "level_ru_02_04"],
        "Season 1": ["level_ru_03_01", "level_ru_03_02"],
        "Season 2": ["level_us_04_01", "level_us_04_02"],
        "Season 3": ["level_us_03_01", "level_us_03_02"],
        "Season 4": ["level_ru_04_01", "level_ru_04_02", "level_ru_04_03", "level_ru_04_04"],
        "Season 5": ["level_ru_05_01", "level_ru_05_02"],
        "Season 6": ["level_us_06_01", "level_us_06_02"],
        "Season 7": ["level_us_07_01"],
        "Season 8": ["level_ru_08_01", "level_ru_08_02", "level_ru_08_03", "level_ru_08_04"],
        "Season 9": ["level_us_09_01", "level_us_09_02"],
        "Season 10": ["level_us_10_01", "level_us_10_02"],
        "Season 11": ["level_us_11_01", "level_us_11_02"],
        "Season 12": ["level_us_12_01", "level_us_12_02", "level_us_12_03", "level_us_12_04"],
        "Season 13": ["level_ru_13_01"],
        "Season 14": ["level_us_14_01", "level_us_14_02"],
        "Season 15": ["level_us_15_01", "level_us_15_02"],
        "Season 16": ["level_us_16_01", "level_us_16_02"],
        "Season 17": ["level_ru_17_01", "level_ru_17_02"],
    }
    
    # Feature Whitelist: Strict file AND key-level isolation
    ALLOWED_MUTATIONS = {
        "reveal_map": {
            "files": ["CompleteSave.cfg", "fog_level_{region}.cfg"],
            "keys": ["persistentProfileData.region_unlocked", "SslValue.region_visited"],
            "risk": "SYNC"
        },
        "reveal_upgrades": {
            "files": ["CompleteSave.cfg", "sts_level_{region}.cfg"],
            "keys": ["SslValue.upgradesGiverData"],
            "risk": "SYNC"
        },
        "unlock_watchtowers": {
            "files": ["CompleteSave.cfg", "sts_level_{region}.cfg"],
            "keys": ["SslValue.watchtowersData", "SslValue.viewedWatchtowers"],
            "risk": "SYNC"
        },
        "money": {
            "files": ["CompleteSave.cfg"],
            "keys": ["CompleteSave.SslValue.money"],
            "risk": "CORE"
        },
        "rank": {
            "files": ["CompleteSave.cfg"],
            "keys": ["CompleteSave.SslValue.rank", "CompleteSave.SslValue.experience"],
            "risk": "CORE"
        },
        "diagnostic_check": {
            "files": ["CompleteSave.cfg"],
            "keys": [],
            "risk": "NONE"
        },
        "unlock_garages": {
            "files": ["CompleteSave.cfg"],
            "keys": ["SslValue.levelGarageStatuses", "SslValue.discoveredObjects", "SslValue.garagesData"],
            "risk": "CORE"
        },
        "discover_trucks": {
            "files": ["CompleteSave.cfg"],
            "keys": ["persistentProfileData.discoveredTrucks"],
            "risk": "CORE"
        },
        "unlock_maps": {
            "files": ["CompleteSave.cfg"],
            "keys": ["persistentProfileData.knownRegions", "visitedLevels"],
            "risk": "CORE"
        },
        "fix_recovery": {
            "files": ["CompleteSave.cfg"],
            "keys": ["SslValue.discoveredObjects", "SslValue.garagesData"],
            "risk": "SYNC"
        },
        "complete_objective": {
            "files": ["CompleteSave.cfg"],
            "keys": ["SslValue.finishedObjs", "objectiveStates"],
            "risk": "CORE"
        },
        "unlock_achievements": {
            "files": ["CommonSslSave.cfg", "CommonSslSave.dat"],
            "keys": ["achievementStates"],
            "risk": "NEW"
        },
        "reset_task": {
            "files": ["CompleteSave.cfg"],
            "keys": ["SslValue.tasksData", "SslValue.completedTasks", "SslValue.finishedObjectives"],
            "risk": "SYNC"
        },
        "repair_vehicle": {
            "files": ["sts_level_{region}.cfg"],
            "keys": [],
            "risk": "BINARY"
        },
        "discover_vehicle": {
            "files": ["CompleteSave.cfg"],
            "keys": ["persistentProfileData.discoveredTrucks"],
            "risk": "CORE"
        },
        "garage_vehicle": {
            "files": ["sts_level_{region}.cfg"],
            "keys": [],
            "risk": "BINARY"
        },
        "move_vehicle": {
            "files": ["sts_level_{region}.cfg"],
            "keys": [],
            "risk": "BINARY"
        },
        "move_trailer": {
            "files": ["sts_level_{region}.cfg"],
            "keys": [],
            "risk": "BINARY"
        },
        "repair_trailer": {
            "files": ["sts_level_{region}.cfg"],
            "keys": [],
            "risk": "BINARY"
        },
        "set_cargo": {
            "files": ["sts_level_{region}.cfg"],
            "keys": [],
            "risk": "BINARY"
        },
        "discover_upgrade": {
            "files": ["CompleteSave.cfg", "sts_level_{region}.cfg"],
            "keys": ["SslValue.discoveredUpgrades"],
            "risk": "CORE"
        },
        "complete_objective": {
            "files": ["CompleteSave.cfg", "CommonSslSave.cfg"],
            "keys": ["SslValue.finishedObjs", "objectiveStates", "SslValue.money", "SslValue.experience"],
            "risk": "CORE"
        },
        "accept_objective": {
            "files": ["CompleteSave.cfg"],
            "keys": ["SslValue.activatedObjectives", "objectiveStates"],
            "risk": "CORE"
        }
    }
    
    def get_feature_risk(self, feature: str) -> str:
        return self.ALLOWED_MUTATIONS.get(feature, {}).get("risk", "UNKNOWN")
    
    # Legacy FEATURE_WHITELIST (kept for compatibility during migration)
    FEATURE_WHITELIST = {k: v["files"] for k, v in ALLOWED_MUTATIONS.items()}
    
    # Mandatory Linkage Mapping
    # (Feature, Region) -> List of required global/file mutations
    FEATURE_LINKAGES = {
        "reveal_map": [
            {"target": "CompleteSave.cfg", "key": "persistentProfileData.region_unlocked", "value": 2},
            {"target": "fog_level_{region}.cfg", "action": "binary_procedural_reveal"}
        ],
        "reveal_upgrades": [
            {"target": "CompleteSave.cfg", "key": "SslValue.upgradesGiverData", "action": "merge_reference_ids"},
            {"target": "sts_level_{region}.cfg", "action": "binary_sts_linkage_sync"}
        ],
        "unlock_watchtowers": [
            {"target": "CompleteSave.cfg", "key": "SslValue.watchtowersData", "action": "merge_reference_ids"},
            {"target": "CompleteSave.cfg", "key": "SslValue.viewedWatchtowers", "action": "merge_reference_ids"},
            {"target": "sts_level_{region}.cfg", "action": "binary_sts_linkage_sync"}
        ],
        "money": [
            {"target": "CompleteSave.cfg", "key": "CompleteSave.SslValue.money", "value": "{value}"}
        ],
        "rank": [
            {"target": "CompleteSave.cfg", "key": "CompleteSave.SslValue.rank", "value": "{value}"},
            {"target": "CompleteSave.cfg", "key": "CompleteSave.SslValue.experience", "value": "{xp_value}"}
        ],
        "diagnostic_check": [],
        "unlock_garages": [
            {"target": "CompleteSave.cfg", "key": "SslValue.levelGarageStatuses", "action": "unlock_region_garages"},
            {"target": "CompleteSave.cfg", "key": "SslValue.discoveredObjects", "action": "sync_garage_entrances"},
            {"target": "CompleteSave.cfg", "key": "SslValue.garagesData", "action": "init_garage_data"}
        ],
        "discover_trucks": [
            {"target": "CompleteSave.cfg", "key": "persistentProfileData.discoveredTrucks", "action": "discover_region_trucks"}
        ],
        "unlock_maps": [
            {"target": "CompleteSave.cfg", "key": "persistentProfileData.knownRegions", "action": "merge_list", "value": "{region}"},
            {"target": "CompleteSave.cfg", "key": "visitedLevels", "action": "merge_list_levels", "value": "{region}"}
        ],
        "fix_recovery": [
            {"target": "CompleteSave.cfg", "key": "SslValue.discoveredObjects", "action": "sync_recovery_links"},
            {"target": "CompleteSave.cfg", "key": "SslValue.garagesData", "action": "init_garage_data"}
        ],
        "complete_objective": [
            {"target": "CompleteSave.cfg", "action": "accept_objective", "value": "{objective_id}"},
            {"target": "CompleteSave.cfg", "key": "SslValue.finishedObjs", "action": "mark_finished", "value": "{objective_id}"},
            {"target": "CompleteSave.cfg", "key": "objectiveStates", "action": "update_objective_state", "value": "{objective_id}"},
            {"target": "CompleteSave.cfg", "action": "apply_objective_rewards", "value": "{objective_id}"},
            {"target": "CommonSslSave.cfg", "action": "sync_global_objective", "value": "{objective_id}"},
            {"target": "sts_level_{region}.cfg", "action": "binary_sts_objective_sync", "value": "{objective_id}"}
        ],
        "unlock_achievements": [
            {"target": "CommonSslSave.cfg", "key": "achievementStates", "action": "update_achievement", "value": "{achievement_id}"}
        ],
        "reset_task": [
            {"target": "CompleteSave.cfg", "key": "SslValue.tasksData", "action": "reset_task_machine", "value": "{task_id}"},
            {"target": "CompleteSave.cfg", "key": "SslValue.completedTasks", "action": "remove_from_list", "value": "{task_id}"},
            {"target": "CompleteSave.cfg", "key": "SslValue.finishedObjectives", "action": "remove_from_list", "value": "{task_id}"},
            {"target": "CompleteSave.cfg", "key": "objectiveStates", "action": "remove_objective_state", "value": "{task_id}"}
        ],
        "repair_vehicle": [
            {"target": "sts_level_{region}.cfg", "action": "binary_repair_vehicle", "value": "{value}"}
        ],
        "discover_vehicle": [
            {"target": "CompleteSave.cfg", "key": "persistentProfileData.discoveredTrucks", "action": "add_to_list", "value": "{value}"}
        ],
        "garage_vehicle": [
            {"target": "sts_level_{region}.cfg", "action": "binary_garage_vehicle", "value": "{value}"}
        ],
        "move_vehicle": [
            {"target": "sts_level_{region}.cfg", "action": "binary_move_vehicle", "value": "{value}"}
        ],
        "move_trailer": [
            {"target": "sts_level_{region}.cfg", "action": "binary_move_trailer", "value": "{value}"}
        ],
        "repair_trailer": [
            {"target": "sts_level_{region}.cfg", "action": "binary_repair_trailer", "value": "{value}"}
        ],
        "set_cargo": [
            {"target": "sts_level_{region}.cfg", "action": "binary_set_cargo", "value": "{value}"}
        ],
        "discover_upgrade": [
            {"target": "CompleteSave.cfg", "key": "SslValue.discoveredUpgrades", "action": "add_to_list", "value": "{value}"},
            {"target": "sts_level_{region}.cfg", "action": "binary_sts_upgrade_removal", "value": "{value}"}
        ],
        "accept_objective": [
            {"target": "CompleteSave.cfg", "key": "SslValue.activatedObjectives", "action": "add_to_list", "value": "{objective_id}"},
            {"target": "CompleteSave.cfg", "key": "objectiveStates", "action": "update_objective_state", "value": "{objective_id}", "status": "ACTIVATED"}
        ]
    }

    def __init__(self, reference_cache_path: str):
        self.reference_cache_path = reference_cache_path
        self.patterns = {}
        self.save_context = None
        self.slot_context = None
        self._load_reference_data()

    def set_save_context(self, save_context: dict):
        """[v110.40] Link to the global folder context."""
        self.save_context = save_context

    def set_slot_context(self, slot_context):
        self.slot_context = slot_context

    def _load_reference_data(self):
        if os.path.exists(self.reference_cache_path):
            with open(self.reference_cache_path, 'r') as f:
                self.patterns = json.load(f)

    def resolve(self, feature: str, region: str, value: Any = None, xp_value: Any = None, 
                objective_id: str = None, achievement_id: str = None, 
                supplemental_data: Dict[str, Any] = None) -> Tuple[List[str], List[Dict[str, Any]]]:
        """
        Returns a (file_whitelist, mutation_steps) tuple for the given feature.
        Now context-aware via save_context.
        """
        if feature not in self.ALLOWED_MUTATIONS:
            raise ValueError(f"Unknown feature: {feature}")

        # 1. Expand Whitelist using Save Context if available
        raw_files = self.ALLOWED_MUTATIONS[feature]["files"]
        final_whitelist = []
        
        for f_pattern in raw_files:
            resolved = None
            if "CompleteSave" in f_pattern:
                resolved = self.save_context["slot"]["active"] if self.save_context else f_pattern
            elif "CommonSslSave" in f_pattern:
                # Find the global common file from registry
                resolved = next((f for f, info in self.save_context["files"].items() if info["type"] == "progression"), None) if self.save_context else f_pattern
            elif "sts_level_" in f_pattern:
                 # [v110.40 FIX 1/2] Selective STS Linkage & Map Resolution
                 map_id = region.lower()
                 if feature == "complete_objective":
                     meta = self.OBJECTIVE_METADATA.get(objective_id)
                     if meta and meta.get("affects_world"):
                         map_id = meta.get("map", map_id)
                     else:
                         continue # Skip STS for logical-only objectives
                 
                 resolved = next((f for f, info in self.save_context["files"].items() if info["type"] == "objectives" and map_id in info["maps"]), None)
                 if not resolved and not self.save_context:
                      # Fallback if no context (legacy/tests)
                      resolved = f_pattern.replace("{region}", map_id)
            elif "fog_level_" in f_pattern:
                 map_id = region.lower()
                 resolved = next((f for f, info in self.save_context["files"].items() if info["type"] == "fog" and map_id in info["maps"]), None) if self.save_context else f_pattern.replace("{region}", map_id)
            else:
                 resolved = f_pattern

            if resolved: final_whitelist.append(resolved)
        
        # 2. Get Mandatory Mutations and Resolve Placeholders
        mutations = []
        if feature in self.FEATURE_LINKAGES:
            for step in self.FEATURE_LINKAGES[feature]:
                processed_step = step.copy()
                
                # Resolve Target Path via Context
                target_pattern = processed_step.get("target", "")
                resolved_target = None
                
                if "CompleteSave" in target_pattern:
                    resolved_target = self.save_context["slot"]["active"] if self.save_context else target_pattern
                elif "CommonSslSave" in target_pattern:
                    resolved_target = next((f for f, info in self.save_context["files"].items() if info["type"] == "progression"), None) if self.save_context else target_pattern
                elif "sts_level_" in target_pattern:
                    # [v110.43] Conditional STS Resolution for Objectives
                    map_id = region.lower()
                    if feature == "complete_objective":
                        meta = self.OBJECTIVE_METADATA.get(objective_id)
                        if not meta or not meta.get("affects_world"):
                            continue # Skip STS linkage for this objective
                        map_id = meta.get("map", map_id)
                    
                    resolved_target = next((f for f, info in self.save_context["files"].items() if info["type"] == "objectives" and map_id in info["maps"]), None)
                elif "fog_level_" in target_pattern:
                    map_id = region.lower()
                    resolved_target = next((f for f, info in self.save_context["files"].items() if info["type"] == "fog" and map_id in info["maps"]), None)

                if not resolved_target:
                    continue # Skip this mutation step if target cannot be resolved (isolation)
                
                processed_step["target"] = resolved_target
                
                # [v110.40 FIX 1] Inject correct map context for Type B objectives
                if feature == "complete_objective" and objective_id in self.OBJECTIVE_METADATA:
                    meta = self.OBJECTIVE_METADATA[objective_id]
                    if meta.get("affects_world"):
                        region = meta.get("map", region)

                # Resolve Value Placeholders
                v = processed_step.get("value")
                if isinstance(v, str):
                    v = v.replace("{value}", str(value) if value is not None else "")
                    v = v.replace("{xp_value}", str(xp_value) if xp_value is not None else "")
                    v = v.replace("{objective_id}", str(objective_id) if objective_id is not None else "")
                    v = v.replace("{achievement_id}", str(achievement_id) if achievement_id is not None else "")
                    v = v.replace("{task_id}", str(value) if value is not None else "")
                    v = v.replace("{region}", str(region) if region is not None else "")
                    processed_step["value"] = v
                
                # Inject Supplemental Data or Compiled Patterns for Actions
                action = processed_step.get("action")
                if action == "merge_reference_ids":
                    # Determine source key (mapped from FEATURE_LINKAGES or specific keys)
                    # For now, it retrieves from global_patterns based on the key
                    key = processed_step.get("key", "")
                    if "upgradesGiverData" in key:
                         processed_step["value"] = self.patterns.get("global_patterns", {}).get("CompleteSave", {}).get("upgradesGiverData", [])
                    elif "watchtowersData" in key or "viewedWatchtowers" in key:
                         processed_step["value"] = self.patterns.get("global_patterns", {}).get("CompleteSave", {}).get("watchpoints_list", []) # Heuristic
                
                if action and supplemental_data and action in supplemental_data:
                    processed_step["value"] = supplemental_data[action]
                
                mutations.append(processed_step)
        
        # 3. Edge-Case Hardening: Final Resolver Validation
        self.validate_resolver_output(feature, final_whitelist, mutations)
        
        return final_whitelist, mutations

    def validate_resolver_output(self, feature: str, whitelist: List[str], mutations: List[Dict[str, Any]]):
        """Ensures that the resolver doesn't generate mutations outside its permitted scope."""
        if feature not in self.ALLOWED_MUTATIONS:
             print(f"[DEBUG] Feature '{feature}' NOT in ALLOWED_MUTATIONS! Keys: {list(self.ALLOWED_MUTATIONS.keys())}")
        allowed_keys = self.ALLOWED_MUTATIONS[feature]["keys"]
        for m in mutations:
            target = m.get("target")
            if target and target not in whitelist:
                raise SecurityError(f"Resolver output targets file '{target}' which is not in the whitelist for feature '{feature}'")
            
            key = m.get("key")
            if key:
                # v110.31 Hardening: Canonical Path Guard
                if "CommonSslSave" not in target and not key.startswith("SslValue.") and not key.startswith("CompleteSave.SslValue."):
                     if key not in ["rank", "money", "experience"]: # Legacy exceptions
                         raise SecurityError(f"Non-canonical path: Feature '{feature}' attempted to modify '{key}' outside SslValue.")

                # Key-level validation
                is_allowed = False
                for allowed in allowed_keys:
                    if key == allowed or key.startswith(allowed + ".") or allowed.startswith(key + "."):
                        is_allowed = True
                        break
                if not is_allowed:
                    raise SecurityError(f"Resolver output targets key '{key}' which is not permitted for feature '{feature}'")

    def validate_scope(self, feature: str, modified_keys: List[str]) -> bool:
        """Enforces Feature Isolation Guarantee at the key level."""
        if feature not in self.ALLOWED_MUTATIONS: return False
        
        allowed_keys = self.ALLOWED_MUTATIONS[feature]["keys"]
        for key in modified_keys:
            # Check if key is a sub-path of an allowed key or vice versa
            is_allowed = False
            for allowed in allowed_keys:
                if key == allowed or key.startswith(allowed + ".") or allowed.startswith(key + "."):
                    is_allowed = True
                    break
            if not is_allowed:
                print(f"[Resolver] Scope Violation: Feature '{feature}' attempted to modify '{key}' (Blocked)")
                return False
        return True
