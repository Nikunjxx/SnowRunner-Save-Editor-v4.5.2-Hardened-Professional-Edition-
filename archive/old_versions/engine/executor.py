import os
import zlib
import json
from typing import Dict, Any, List, Optional

MAGIC_AK = b'\x41\x4b\x05\x00'
MAGIC_D3 = b'\xd3\xa6\x02\x00'

class ProceduralMutator:
    """
    Handles deterministic, isolated save mutations (e.g. Reveal Map).
    v110.31 Platinum Edition: Strictly anchored to SslValue.
    """
    def __init__(self, target_folder: str):
        self.target_folder = target_folder

    def _get_ssl_root(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Strictly anchors mutation to the canonical SslValue state container."""
        if "CompleteSave" in data:
            if "SslValue" not in data["CompleteSave"]:
                data["CompleteSave"]["SslValue"] = {}
            return data["CompleteSave"]["SslValue"]
        if "SslValue" not in data:
            data["SslValue"] = {}
        return data["SslValue"]

    def _normalize_path(self, path: str) -> str:
        """Ensures all JSON mutation paths are relative to SslValue root."""
        if path.startswith("CompleteSave.SslValue."):
            return path.replace("CompleteSave.SslValue.", "")
        if path.startswith("SslValue."):
            return path.replace("SslValue.", "")
        return path

    def _get_nested_val(self, data: Dict[str, Any], path: str) -> Any:
        """Safe nested value getter with Canonical Anchoring."""
        if "CompleteSave" in data or "SslValue" in data:
            root = self._get_ssl_root(data)
            normalized_path = self._normalize_path(path)
        else:
            root = data
            normalized_path = path
            
        parts = normalized_path.split(".")
        curr = root
        for part in parts:
            if isinstance(curr, dict) and part in curr:
                curr = curr[part]
            else:
                return None
        return curr

    def _set_nested_key(self, data: Dict[str, Any], path: str, value: Any, modified_keys_out: List[str]):
        """Safe nested key setter with Canonical Anchoring."""
        ssl_root = self._get_ssl_root(data)
        normalized_path = self._normalize_path(path)
        
        parts = normalized_path.split(".")
        curr = ssl_root
        for i, part in enumerate(parts[:-1]):
            if part not in curr or not isinstance(curr[part], dict):
                curr[part] = {}
            curr = curr[part]
        
        target_key = parts[-1]
        curr[target_key] = value
        modified_keys_out.append(path)

    def apply_reveal_map(self, region_id: str, dry_run: bool = False) -> bool:
        """Procedural fog reveal logic."""
        fog_file = f"fog_level_{region_id.lower()}.cfg"
        fog_path = os.path.join(self.target_folder, fog_file)
        if not os.path.exists(fog_path): return False
        if dry_run: return True
        try:
            with open(fog_path, 'rb') as f: data = f.read()
            header = data[:4]
            if header not in [MAGIC_AK, MAGIC_D3]: return False
            payload = zlib.decompress(data[4:])
            revealed_payload = bytearray([0x00] * len(payload))
            recompressed = zlib.compress(revealed_payload, level=zlib.Z_BEST_COMPRESSION)
            with open(fog_path, 'wb') as f: f.write(header + recompressed)
            return True
        except: return False

    def apply_global_linkage(self, complete_save_path: str, mutation_steps: List[Dict[str, Any]], resolver_ref=None, feature_ref=None, dry_run: bool = False, region_ref: str = "GLOBAL") -> bool:
        """Action Dispatcher with Scope Guard."""
        if not os.path.exists(complete_save_path): return False
        try:
            with open(complete_save_path, 'rb') as f: raw_data = f.read()
            header = MAGIC_AK if raw_data.startswith(MAGIC_AK) else (MAGIC_D3 if raw_data.startswith(MAGIC_D3) else b'')
            text = zlib.decompress(raw_data[4:]).decode('utf-8', errors='replace') if header else raw_data.decode('utf-8', errors='replace')
            js_data = json.loads(text.strip().split('\x00')[0])
            modified_keys = []
            for step in mutation_steps:
                action, key, value = step.get("action"), step.get("key"), step.get("value")
                if action:
                    handler = getattr(self, f"_action_{action}", None)
                    if handler: handler(js_data, key, value, modified_keys, region_ref)
                elif key:
                    self._set_nested_key(js_data, key, value, modified_keys)
            if dry_run: return True
            if modified_keys:
                updated = json.dumps(js_data, separators=(',', ':'))
                with open(complete_save_path, 'wb' if header else 'w') as f:
                    f.write(header + zlib.compress(updated.encode('utf-8')) if header else updated)
            return True
        except Exception as e:
            print(f"[Mutator] linkage error: {e}")
            return False

    # --- Action Handlers ---
    def _action_unlock_region_garages(self, data, key, value, mods, region):
        target = self._get_nested_val(data, key)
        if isinstance(target, dict):
            for lvl in (value if isinstance(value, list) else []):
                target[lvl] = 2
                mods.append(f"{key}.{lvl}")

    def _action_sync_garage_entrances(self, data, key, value, mods, region):
        entrance_map = value if isinstance(value, dict) else {}
        target = self._get_nested_val(data, key)
        if not isinstance(target, list): return
        lg_status = self._get_nested_val(data, "SslValue.levelGarageStatuses") or {}
        for lvl, zone in entrance_map.items():
            if lg_status.get(lvl) == 2 and zone not in target:
                target.append(zone)
                mods.append(f"{key}.{zone}")

    def _action_init_garage_data(self, data, key, value, mods, region):
        target = self._get_nested_val(data, key)
        if not isinstance(target, dict): return
        lg_status = self._get_nested_val(data, "SslValue.levelGarageStatuses") or {}
        for lvl, status in lg_status.items():
            if status == 2 and lvl not in target:
                target[lvl] = value.copy() if isinstance(value, dict) else {}
                mods.append(f"{key}.{lvl}")

    def _action_discover_region_trucks(self, data, key, value, mods, region):
        target = self._get_nested_val(data, key)
        if not isinstance(target, dict): return
        for m in (value if isinstance(value, list) else []):
            for t_orig in target:
                if m.lower() in t_orig.lower():
                    if "all" in target[t_orig]:
                        target[t_orig]["current"] = target[t_orig]["all"]
                        mods.append(f"{key}.{t_orig}")

    def _action_merge_list(self, data, key, value, mods, region):
        target = self._get_nested_val(data, key)
        if isinstance(target, list) and value not in target:
            target.append(value)
            mods.append(f"{key}.{value}")

    def _action_mark_finished(self, data, key, value, mods, region):
        target = self._get_nested_val(data, key)
        if isinstance(target, dict): target[value] = True
        elif isinstance(target, list) and value not in target: target.append(value)
        mods.append(f"{key}.{value}")

    def _action_update_objective_state(self, data, key, value, mods, region):
        target = self._get_nested_val(data, key)
        if not isinstance(target, dict): return
        target[value] = target.get(value, {})
        if isinstance(target[value], dict):
            target[value]["isFinished"] = True
            target[value]["wasCompletedAtLeastOnce"] = True
            target[value]["lastStatus"] = 3
            mods.append(f"{key}.{value}")

    def _action_update_achievement(self, data, key, value, mods, region):
        target = self._get_nested_val(data, key)
        if not isinstance(target, dict): return
        target[value] = target.get(value, {"isUnlocked": True, "currentValue": 1, "$type": "IntAchievementState"})
        if isinstance(target[value], dict): target[value]["isUnlocked"] = True
        mods.append(f"{key}.{value}")

    def _action_reset_task_machine(self, data, key, value, mods, region):
        tasks = self._get_nested_val(data, key)
        if isinstance(tasks, dict) and value in tasks:
            task = tasks[value]
            task["isFinished"] = False
            task["isAccepted"] = False
            if "wasCompleted" in task: task["wasCompleted"] = False
            for obj in task.get("objectives", []):
                obj["current"] = 0
                obj["isCompleted"] = False
                if "visited" in obj: obj["visited"] = False
            mods.append(f"{key}.{value}")

    def _action_remove_from_list(self, data, key, value, mods, region):
        target = self._get_nested_val(data, key)
        if isinstance(target, list) and value in target: target.remove(value)
        elif isinstance(target, dict) and value in target: del target[value]
        mods.append(f"{key}.{value}")

    def _action_binary_procedural_reveal(self, data, key, value, mods, region):
        self.apply_reveal_map(region)

    def _action_binary_sts_linkage_sync(self, data, key, value, mods, region):
        sts_path = os.path.join(self.target_folder, f"sts_level_{region.lower()}.cfg")
        if not os.path.exists(sts_path): return
        try:
            with open(sts_path, 'rb') as f: raw = f.read()
            header = raw[:4]
            if header in [MAGIC_AK, MAGIC_D3]:
                payload = zlib.decompress(raw[4:])
                with open(sts_path, 'wb') as f: f.write(header + zlib.compress(payload))
        except: pass

    def _action_sync_recovery_links(self, data, key, value, mods, region):
        self._action_sync_garage_entrances(data, key, value, mods, region)

    def _action_complete_contest(self, data, key, value, mods, region):
        """Standardizes contest completion including sync lists."""
        # 1. finishedObjs
        finished = self._get_nested_val(data, "SslValue.finishedObjs")
        if isinstance(finished, dict): finished[value] = True
        elif isinstance(finished, list) and value not in finished: finished.append(value)
        mods.append(f"SslValue.finishedObjs.{value}")
        
        # 2. contestTimes
        times = self._get_nested_val(data, "SslValue.contestTimes")
        if isinstance(times, dict):
            times[value] = 1 # Mark as 1 second or similar success
            mods.append(f"SslValue.contestTimes.{value}")
            
        # 3. viewedUnactivatedObjectives (cleanup)
        viewed = self._get_nested_val(data, "SslValue.viewedUnactivatedObjectives")
        if isinstance(viewed, list) and value in viewed:
            viewed.remove(value)
            mods.append(f"SslValue.viewedUnactivatedObjectives.{value}.REMOVED")

    def _action_ensure_dict(self, data, key, value, mods, region):
        root = self._get_ssl_root(data)
        curr = root
        for part in self._normalize_path(key).split("."):
            if part not in curr or not isinstance(curr[part], dict):
                curr[part] = {}
            curr = curr[part]

    def _action_ensure_list(self, data, key, value, mods, region):
        root = self._get_ssl_root(data)
        parts = self._normalize_path(key).split(".")
        curr = root
        for part in parts[:-1]:
            if part not in curr or not isinstance(curr[part], dict):
                curr[part] = {}
            curr = curr[part]
        if not isinstance(curr.get(parts[-1]), list):
            curr[parts[-1]] = []

    def _action_add_to_list(self, data, key, value, mods, region):
        target = self._get_nested_val(data, key)
        if isinstance(target, list) and value not in target:
            target.append(value)
            mods.append(f"{key}.{value}")

    def _action_binary_repair_vehicle(self, data, key, value, mods, region):
        """Resets damage in the specified region's STS file."""
        if not region or region == "GLOBAL": return
        sts_path = os.path.join(self.target_folder, f"sts_level_{region.lower()}.cfg")
        if not os.path.exists(sts_path): return
        
        try:
            with open(sts_path, 'rb') as f: raw = f.read()
            header = raw[:4]
            payload = zlib.decompress(raw[4:])
            # sts files are usually JSON once decompressed
            sts_json = json.loads(payload.decode('utf-8', errors='replace'))
            
            modified = False
            # Search for the vehicle in the STS world state
            # Usually under 'trucks' or similar top-level key
            for k in ["trucks", "objects"]:
                if k in sts_json and isinstance(sts_json[k], dict):
                    for v_key, v_data in sts_json[k].items():
                        if value in v_key or (isinstance(v_data, dict) and (v_data.get("type") == value)):
                            if "damage" in v_data:
                                v_data["damage"] = 0
                                modified = True
            
            if modified:
                updated = json.dumps(sts_json, separators=(',', ':'))
                with open(sts_path, 'wb') as f:
                    f.write(header + zlib.compress(updated.encode('utf-8')))
                mods.append(f"BINARY.REPAIR.{value}")
        except Exception as e:
             print(f"[Mutator] repair error for {value}: {e}")

    def _action_binary_garage_vehicle(self, data, key, value, mods, region):
        """Relocates vehicle to garage in the specified region's STS file."""
        if not region or region == "GLOBAL": return
        sts_path = os.path.join(self.target_folder, f"sts_level_{region.lower()}.cfg")
        if not os.path.exists(sts_path): return
        
        try:
            with open(sts_path, 'rb') as f: raw = f.read()
            header = raw[:4]
            payload = zlib.decompress(raw[4:])
            sts_json = json.loads(payload.decode('utf-8', errors='replace'))
            
            modified = False
            # Default Garage Position (Michigan, Black River heuristic)
            # In a real app, we should use map-specific garage coords.
            # Using (0, 10, 0) as a safe 'Return Zone' fallback.
            GARAGE_COORDS = {"x": 0.0, "y": 10.0, "z": 0.0} 
            
            for k in ["trucks", "objects"]:
                if k in sts_json and isinstance(sts_json[k], dict):
                    for v_key, v_data in sts_json[k].items():
                        if value in v_key or (isinstance(v_data, dict) and (v_data.get("type") == value)):
                            if "position" in v_data:
                                v_data["position"] = GARAGE_COORDS
                                modified = True
            
            if modified:
                updated = json.dumps(sts_json, separators=(',', ':'))
                with open(sts_path, 'wb') as f:
                    f.write(header + zlib.compress(updated.encode('utf-8')))
                mods.append(f"BINARY.GARAGE.{value}")
        except Exception as e:
            print(f"[Mutator] garage error for {value}: {e}")
