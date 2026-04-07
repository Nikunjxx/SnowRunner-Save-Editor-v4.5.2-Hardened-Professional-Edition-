import os
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
        "modify_time": {
            "files": ["CompleteSave.cfg"],
            "keys": ["SslValue.timeSettingsDay", "SslValue.timeSettingsNight", "SslValue.isAbleToSkipTime"],
            "risk": "CORE"
        },
        "complete_contest": {
            "files": ["CompleteSave.cfg"],
            "keys": ["SslValue.finishedObjs", "SslValue.contestTimes", "SslValue.viewedUnactivatedObjectives"],
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
            {"target": "CompleteSave.cfg", "key": "SslValue.finishedObjs", "action": "mark_finished", "value": "{objective_id}"},
            {"target": "CompleteSave.cfg", "key": "objectiveStates", "action": "update_objective_state", "value": "{objective_id}"}
        ],
        "unlock_achievements": [
            {"target": "CommonSslSave.cfg", "key": "achievementStates", "action": "update_achievement", "value": "{achievement_id}"}
        ],
        "reset_task": [
            {"target": "CompleteSave.cfg", "key": "SslValue.tasksData", "action": "reset_task_machine", "value": "{task_id}"},
            {"target": "CompleteSave.cfg", "key": "SslValue.completedTasks", "action": "remove_from_list", "value": "{task_id}"},
            {"target": "CompleteSave.cfg", "key": "SslValue.finishedObjectives", "action": "remove_from_list", "value": "{task_id}"}
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
        "modify_time": [
            {"target": "CompleteSave.cfg", "key": "SslValue.timeSettingsDay", "value": "{value}"},
            {"target": "CompleteSave.cfg", "key": "SslValue.timeSettingsNight", "value": "{xp_value}"},
            {"target": "CompleteSave.cfg", "key": "SslValue.isAbleToSkipTime", "value": "{supplemental_data}"}
        ],
        "complete_contest": [
            {"target": "CompleteSave.cfg", "action": "complete_contest", "value": "{objective_id}"}
        ]
    }

    def __init__(self, reference_cache_path: str):
        self.reference_cache_path = reference_cache_path
        self.patterns = {}
        self._load_reference_data()

    def _load_reference_data(self):
        if os.path.exists(self.reference_cache_path):
            with open(self.reference_cache_path, 'r') as f:
                self.patterns = json.load(f)

    def resolve(self, feature: str, region: str, value: Any = None, xp_value: Any = None, 
                objective_id: str = None, achievement_id: str = None, 
                supplemental_data: Dict[str, Any] = None) -> Tuple[List[str], List[Dict[str, Any]]]:
        """
        Returns a (file_whitelist, mutation_steps) tuple for the given feature.
        Supports dynamic value injection via {value}, {xp_value}, {objective_id}, {achievement_id}.
        """
        if feature not in self.ALLOWED_MUTATIONS:
            raise ValueError(f"Unknown feature: {feature}")

        # 1. Expand Whitelist with Region
        raw_files = self.ALLOWED_MUTATIONS[feature]["files"]
        final_whitelist = [f.replace("{region}", region.lower()) for f in raw_files]
        
        # 2. Get Mandatory Mutations and Resolve Placeholders
        mutations = []
        if feature in self.FEATURE_LINKAGES:
            for step in self.FEATURE_LINKAGES[feature]:
                processed_step = step.copy()
                
                # Resolve Target Path
                if "target" in processed_step:
                    processed_step["target"] = processed_step["target"].replace("{region}", region.lower())
                
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
