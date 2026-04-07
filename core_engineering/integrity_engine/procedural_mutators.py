import json
import os
import re
import zlib
import struct
from typing import List, Dict, Any, Optional, Tuple
from data.objective_database import get_objective_db

MAGIC_AK = b'\x41\x4b\x05\x00'
MAGIC_D3 = b'\xd3\xa6\x02\x00'

class ProceduralMutator:
    """
    Handles deterministic, isolated save mutations (e.g. Reveal Map).
    v110.40 Platinum Edition: Strictly anchored to SslValue.
    """
    MAX_XP_LEVEL_30 = 128500 # Michigan/Global Level 30 threshold (Approx)

    def __init__(self, target_folder: str):
        self.target_folder = target_folder

    def _write_atomic(self, path: str, data: bytes, manager=None, tx_id: str = None):
        """
        [v110.43] Directs write operation to the Manager's atomic helper 
        ensuring collision-resistant temp naming via tx_id.
        """
        if manager and hasattr(manager, '_atomic_write'):
            return manager._atomic_write(path, data, tx_id=tx_id)
        
        # Local Fallback (v110.43: Minimal JIT + tx_id logic)
        import time
        import uuid
        safe_tx_id = tx_id if tx_id else str(uuid.uuid4())
        temp_path = f"{path}.tmp.{safe_tx_id}"
        
        try:
            if os.path.exists(temp_path): os.remove(temp_path)
            with open(temp_path, "wb") as f:
                f.write(data); f.flush(); os.fsync(f.fileno())
            
            for attempt in range(5):
                # JIT Re-Check (Manager context preferred for full snapshot access)
                if manager and hasattr(manager, '_jit_integrity_recheck'):
                    if not manager._jit_integrity_recheck(path):
                        raise RuntimeError("JIT_STALE_EXCEPTION_MUTATOR")
                
                try:
                    os.replace(temp_path, path)
                    return
                except PermissionError:
                    if attempt < 4: time.sleep(0.2)
                    else: raise
        except Exception as e:
            if os.path.exists(temp_path):
                try: os.remove(temp_path)
                except: pass
            raise

    def _verify_integrity(self, path: str, expected_header: bytes) -> bool:
        """
        [v110.40 FIX 3] Binary Guard: Performs type-aware post-transaction verification.
        - CompleteSave: JSON parseability.
        - STS: Zlib integrity + Structural JSON check.
        - Fog: Zlib integrity + Size consistency.
        """
        if not os.path.exists(path): return False
        filename = os.path.basename(path).lower()
        
        try:
            with open(path, 'rb') as f:
                data = f.read()
            
            # 1. Header Check
            if expected_header and not data.startswith(expected_header):
                return False
            
            # 2. Type-Aware Deep Audit
            if "completesave" in filename:
                # CompleteSave: JSON Parseability
                text = zlib.decompress(data[4:]).decode('utf-8', errors='replace') if expected_header else data.decode('utf-8', errors='replace')
                json.loads(text.strip().split('\x00')[0])
                
            elif "sts_level_" in filename:
                # STS: Zlib + Structural JSON
                if not expected_header: return False # STS is always compressed in SnowRunner
                payload = zlib.decompress(data[4:])
                sts_data = json.loads(payload.decode('utf-8', errors='replace'))
                if "trucks" not in sts_data and "objects" not in sts_data:
                    raise ValueError("STS file missing mandatory world keys.")
                    
            elif "fog_level_" in filename:
                # Fog: Zlib + Size Consistency
                if not expected_header: return False
                payload = zlib.decompress(data[4:])
                # Fog files are typically large binary grids. 
                # Michigan/Taymyr: ~256KB decompressed.
                # Just ensure it's not suspiciously small (< 1KB)
                if len(payload) < 1024:
                    raise ValueError("Fog file payload suspiciously small (Corruption suspected).")
            
            return True
        except Exception as e:
            print(f"[BinaryGuard] Post-write verification failed for {filename}: {e}")
            return False

    # --- Objective Collection Helpers (v110.60) ---
    
    def _parse_id_collection(self, raw):
        if isinstance(raw, dict):
            shape = "dict"
            items = list(raw.keys())
        elif isinstance(raw, list):
            shape = "list"
            items = [x for x in raw if isinstance(x, str)]
        else:
            shape = "list"
            items = []
        return shape, self._dedupe_ids(items)

    def _pack_id_collection(self, shape, items):
        if shape == "dict":
            return {k: True for k in items}
        return list(items)

    def _dedupe_ids(self, ids):
        if not ids: return []
        seen = set()
        out = []
        for x in ids:
            if not x or not isinstance(x, str): continue
            s = x.strip()
            if s and s not in seen:
                out.append(s); seen.add(s)
        return out

    def _seed_objective_state(self, oid):
        return {
            "id": oid,
            "isFinished": False,
            "wasCompletedAtLeastOnce": False,
            "isTimerStarted": True,
            "failReasons": {},
            "stagesState": []
        }

    def _order_collection_items(self, original_items, current_set, priority=None):
        out = []
        seen = set()
        # Keep original order for items still in set
        for x in original_items:
            if x in current_set:
                out.append(x); seen.add(x)
        # Add new items from priority
        if priority:
            for x in priority:
                if x in current_set and x not in seen:
                    out.append(x); seen.add(x)
        # Add any remaining
        for x in current_set:
            if x not in seen:
                out.append(x); seen.add(x)
        return out

    def apply_objective_batch(self, status: str, objective_ids: List[str], manager=None, tx_id: str = None) -> bool:
        """
        [v110.60] Precision Objective Mutation Engine.
        Directly modifies discoveredObjectives, finishedObjs, viewedUnactivatedObjectives, 
        and objectiveStates in the SslValue.
        """
        if not manager or not manager.manager or not manager.manager.SslValue:
            return False
            
        ssl = manager.manager.SslValue
        ids = self._dedupe_ids(objective_ids)
        if not ids: return False
        
        status_norm = status.strip().upper()
        ids_set = set(ids)
        
        def _ensure_state(states, oid):
            state = states.get(oid)
            if not isinstance(state, dict):
                state = self._seed_objective_state(oid)
                states[oid] = state
            return state

        # 1. Parse current collections
        d_shape, d_items = self._parse_id_collection(ssl.get("discoveredObjectives", []))
        f_shape, f_items = self._parse_id_collection(ssl.get("finishedObjs", []))
        v_shape, v_items = self._parse_id_collection(ssl.get("viewedUnactivatedObjectives", []))
        
        d_set, f_set, v_set = set(d_items), set(f_items), set(v_items)
        states = ssl.get("objectiveStates", {})
        if not isinstance(states, dict): states = {}

        # 2. Apply Logical Transitions
        if status_norm == "COMPLETED":
            d_set |= ids_set
            v_set -= ids_set
            f_set |= ids_set
            for oid in ids:
                state = _ensure_state(states, oid)
                state["isFinished"] = True
                state["wasCompletedAtLeastOnce"] = True
                state["isTimerStarted"] = True
        elif status_norm in {"NEW", "LOCKED"}:
            d_set -= ids_set
            v_set -= ids_set
            f_set -= ids_set
            for oid in ids:
                if oid in states:
                    states[oid]["isFinished"] = False
                    states[oid]["wasCompletedAtLeastOnce"] = False
            # Clean up tracked objective if it was one of these
            if str(ssl.get("trackedObjective", "")) in ids_set:
                ssl["trackedObjective"] = ""

        # 3. Pack and Re-order
        ssl["discoveredObjectives"] = self._pack_id_collection(d_shape, self._order_collection_items(d_items, d_set, priority=ids))
        ssl["finishedObjs"] = self._pack_id_collection(f_shape, self._order_collection_items(f_items, f_set, priority=ids))
        ssl["viewedUnactivatedObjectives"] = self._pack_id_collection(v_shape, self._order_collection_items(v_items, v_set, priority=ids))
        ssl["objectiveStates"] = states
        
        return True

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

    def _parse_fog_payload(self, dec_data: bytes) -> Tuple[bytes, bytearray]:
        """
        [v110.50] Precisely separates header (W, H, and optional field) from the fog grid.
        Returns (header_bytes, grid_bytearray).
        """
        if len(dec_data) < 8:
            raise ValueError("Fog payload too small to be valid.")
        
        w, h = struct.unpack("<II", dec_data[:8])
        header_size = 8
        
        # Detect 12-byte header variant (extra field check)
        if len(dec_data) > 12:
            extra = struct.unpack("<I", dec_data[8:12])[0]
            if extra < 10000: # Heuristic for non-pixel data
                header_size = 12
        
        header = dec_data[:header_size]
        grid = bytearray(dec_data[header_size:])
        
        # [v110.51] Fog Grid Boundary Assertions
        if len(grid) == 0:
            raise ValueError("Fog grid parsed as empty payload (Corrupt structure).")
        
        # Final safety check: Grid must match expected dimensions
        if len(grid) != (w * h):
            # Fallback for unexpected padding or footer
            grid = grid[:(w * h)]
            
        return header, grid

    def _rebuild_fog_payload(self, header: bytes, grid: bytearray) -> bytes:
        """Reassembles the fog payload for compression."""
        return header + grid

    def _verify_fog_grid_integrity(self, grid: bytearray, expected_size: int) -> bool:
        """
        [v110.50] Semantic verification of the revealed grid.
        Asserts dimensions and 0x80 fill density.
        """
        if len(grid) != expected_size:
            return False
        
        # Check density (must be > 95% 0x80 filled to be 'Revealed')
        fill_count = grid.count(0x80)
        density = fill_count / len(grid) if len(grid) > 0 else 0
        return density > 0.95

    def apply_reveal_map(self, region_id: str, dry_run: bool = False, manager=None, tx_id: str = None) -> bool:
        """
        [v110.50] Safe Fog Reveal Engine (Golden Clarity 0x80).
        Operates only on existing files found in the save context.
        """
        # 1. Resolve target file from context if available
        candidates = []
        if manager and hasattr(manager, "save_context"):
            # Use indexed context (preferred)
            fog_file = manager.save_context["fog"].get(region_id.lower())
            if fog_file:
                candidates.append(os.path.join(self.target_folder, fog_file))
        
        # Fallback to legacy naming conventions if context missing
        if not candidates:
            for ext in [".dat", ".cfg"]:
                p = os.path.join(self.target_folder, f"fog_level_{region_id.lower()}{ext}")
                if os.path.exists(p): candidates.append(p)

        if not candidates:
            return False # Context-aware: Skip if not visited
            
        if dry_run: return True
        
        success_count = 0
        for fog_path in candidates:
            try:
                with open(fog_path, 'rb') as f: 
                    data = f.read()
                
                header_magic = data[:4]
                if header_magic not in [MAGIC_AK, MAGIC_D3]:
                    continue # Not a valid fog file
                
                # 2. Decompress and Parse
                payload_dec = zlib.decompress(data[4:])
                header_block, grid = self._parse_fog_payload(payload_dec)
                expected_grid_size = len(grid)
                
                # 3. Idempotency Check (Strict bitwise-exact 0x80)
                if all(b == 0x80 for b in grid):
                    success_count += 1
                    continue # Already revealed, skip write
                
                # 4. Golden Clarity Fill (0x80)
                revealed_grid = bytearray([0x80] * expected_grid_size)
                
                # 5. Rebuild and Compress
                final_payload = self._rebuild_fog_payload(header_block, revealed_grid)
                
                # [v110.50] Length Consistency Guard
                if len(final_payload) != len(payload_dec):
                    print(f"[BinaryGuard] Length mismatch during reconstruction for {region_id}. Aborting.")
                    continue

                recompressed = zlib.compress(final_payload, level=6) # Balanced compression
                
                # [v110.50] Round-Trip Compression Validation
                try:
                    if zlib.decompress(recompressed) != final_payload:
                        print(f"[BinaryGuard] Round-trip validation failed for {region_id}. Aborting.")
                        continue
                except Exception as ce:
                    print(f"[BinaryGuard] Compression error for {region_id}: {ce}")
                    continue

                # [v110.43] Atomic Write with TX isolation
                self._write_atomic(fog_path, header_magic + recompressed, manager=manager, tx_id=tx_id)
                
                # 6. Post-Write Verification (Semantic + Binary)
                if self._verify_integrity(fog_path, header_magic):
                    # Deep semantic check
                    with open(fog_path, 'rb') as f: 
                        read_back = f.read()
                    rb_dec = zlib.decompress(read_back[4:])
                    _, rb_grid = self._parse_fog_payload(rb_dec)
                    
                    if self._verify_fog_grid_integrity(rb_grid, expected_grid_size):
                        success_count += 1
                
            except Exception as e:
                print(f"[Mutator] Fog reveal error for {region_id}: {e}")
                continue
                
        return success_count > 0

    def apply_global_linkage(self, complete_save_path: str, mutation_steps: List[Dict[str, Any]], resolver_ref=None, feature_ref=None, dry_run: bool = False, region_ref: str = "GLOBAL", manager=None, tx_id: str = None) -> bool:
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
                    if handler:
                        # [v110.43] Pass manager and tx_id context to handlers for STS/Fog linkage
                        handler(js_data, key, value, modified_keys, region_ref, step=step, manager=manager, tx_id=tx_id)
                elif key:
                    self._set_nested_key(js_data, key, value, modified_keys)
            if dry_run: return True
            if modified_keys:
                updated = json.dumps(js_data, separators=(',', ':'))
                payload = header + zlib.compress(updated.encode('utf-8')) if header else updated.encode('utf-8')
                
                # [v110.43] Atomic Write with TX isolation
                self._write_atomic(complete_save_path, payload, manager=manager, tx_id=tx_id)
                return self._verify_integrity(complete_save_path, header)
            return True
        except Exception as e:
            print(f"[Mutator] linkage error: {e}")
            return False

    # --- Action Handlers ---
    def _action_unlock_region_garages(self, data, key, value, mods, region, **kwargs):
        target = self._get_nested_val(data, key)
        if isinstance(target, dict):
            for lvl in (value if isinstance(value, list) else []):
                target[lvl] = 2
                mods.append(f"{key}.{lvl}")

    def _action_sync_garage_entrances(self, data, key, value, mods, region, **kwargs):
        entrance_map = value if isinstance(value, dict) else {}
        target = self._get_nested_val(data, key)
        if not isinstance(target, list): return
        lg_status = self._get_nested_val(data, "SslValue.levelGarageStatuses") or {}
        for lvl, zone in entrance_map.items():
            if lg_status.get(lvl) == 2 and zone not in target:
                target.append(zone)
                mods.append(f"{key}.{zone}")

    def _action_init_garage_data(self, data, key, value, mods, region, **kwargs):
        target = self._get_nested_val(data, key)
        if not isinstance(target, dict): return
        lg_status = self._get_nested_val(data, "SslValue.levelGarageStatuses") or {}
        for lvl, status in lg_status.items():
            if status == 2 and lvl not in target:
                target[lvl] = value.copy() if isinstance(value, dict) else {}
                mods.append(f"{key}.{lvl}")

    def _action_discover_region_trucks(self, data, key, value, mods, region, **kwargs):
        target = self._get_nested_val(data, key)
        if not isinstance(target, dict): return
        for m in (value if isinstance(value, list) else []):
            for t_orig in target:
                if m.lower() in t_orig.lower():
                    if "all" in target[t_orig]:
                        target[t_orig]["current"] = target[t_orig]["all"]
                        mods.append(f"{key}.{t_orig}")

    def _action_merge_list(self, data, key, value, mods, region, **kwargs):
        target = self._get_nested_val(data, key)
        if isinstance(target, list) and value not in target:
            target.append(value)
            mods.append(f"{key}.{value}")

    def _action_mark_finished(self, data, key, value, mods, region, **kwargs):
        target = self._get_nested_val(data, key)
        if isinstance(target, dict): target[value] = True
        elif isinstance(target, list) and value not in target: target.append(value)
        mods.append(f"{key}.{value}")

    def _action_update_objective_state(self, data, key, value, mods, region, **kwargs):
        target = self._get_nested_val(data, key)
        if not isinstance(target, dict): return
        target[value] = target.get(value, {})
        if isinstance(target[value], dict):
            target[value]["isFinished"] = True
            target[value]["lastStatus"] = 3
            mods.append(f"{key}.{value}")

    def _action_update_achievement(self, data, key, value, mods, region, **kwargs):
        target = self._get_nested_val(data, key)
        if not isinstance(target, dict): return
        target[value] = target.get(value, {"isUnlocked": True, "currentValue": 1, "$type": "IntAchievementState"})
        if isinstance(target[value], dict): target[value]["isUnlocked"] = True
        mods.append(f"{key}.{value}")

    def _action_reset_task_machine(self, data, key, value, mods, region, **kwargs):
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

    def _action_remove_from_list(self, data, key, value, mods, region, **kwargs):
        target = self._get_nested_val(data, key)
        if isinstance(target, list) and value in target: target.remove(value)
        elif isinstance(target, dict) and value in target: del target[value]
        mods.append(f"{key}.{value}")

    def _action_binary_procedural_reveal(self, data, key, value, mods, region, **kwargs):
        self.apply_reveal_map(region, manager=kwargs.get("manager"), tx_id=kwargs.get("tx_id"))

    def _action_binary_sts_linkage_sync(self, data, key, value, mods, region, **kwargs):
        sts_path = os.path.join(self.target_folder, f"sts_level_{region.lower()}.cfg")
        if not os.path.exists(sts_path): return
        try:
            with open(sts_path, 'rb') as f: raw = f.read()
            header = raw[:4]
            if header in [MAGIC_AK, MAGIC_D3]:
                payload = zlib.decompress(raw[4:])
                self._write_atomic(sts_path, header + zlib.compress(payload), manager=kwargs.get("manager"), tx_id=kwargs.get("tx_id"))
        except: pass

    def _action_sync_recovery_links(self, data, key, value, mods, region, **kwargs):
        self._action_sync_garage_entrances(data, key, value, mods, region)

    def _action_ensure_dict(self, data, key, value, mods, region, **kwargs):
        root = self._get_ssl_root(data)
        curr = root
        for part in self._normalize_path(key).split("."):
            if part not in curr or not isinstance(curr[part], dict):
                curr[part] = {}
            curr = curr[part]

    def _action_ensure_list(self, data, key, value, mods, region, **kwargs):
        root = self._get_ssl_root(data)
        parts = self._normalize_path(key).split(".")
        curr = root
        for part in parts[:-1]:
            if part not in curr or not isinstance(curr[part], dict):
                curr[part] = {}
            curr = curr[part]
        if not isinstance(curr.get(parts[-1]), list):
            curr[parts[-1]] = []

    def _action_add_to_list(self, data, key, value, mods, region, **kwargs):
        target = self._get_nested_val(data, key)
        if isinstance(target, list) and value not in target:
            target.append(value)
            mods.append(f"{key}.{value}")

    def _action_binary_repair_vehicle(self, data, key, value, mods, region, **kwargs):
        """Resets damage and refills fuel in the specified region's STS file."""
        step = kwargs.get("step", {})
        target_file = step.get("target") or f"sts_level_{region.lower()}.cfg"
        sts_path = os.path.join(self.target_folder, target_file)
        if not os.path.exists(sts_path): return
        
        try:
            with open(sts_path, 'rb') as f: raw = f.read()
            header = raw[:4]
            payload = zlib.decompress(raw[4:])
            sts_json = json.loads(payload.decode('utf-8', errors='replace'))
            
            modified = False
            for k in ["trucks", "objects"]:
                if k in sts_json and isinstance(sts_json[k], dict):
                    for v_key, v_data in sts_json[k].items():
                        if value in v_key or (isinstance(v_data, dict) and (v_data.get("type") == value)):
                            # 1. Reset Damage
                            if "damage" in v_data:
                                v_data["damage"] = 0
                                modified = True
                            # 2. Refill Fuel (if applicable)
                            if "fuel" in v_data:
                                # Note: Some trucks have specific max fuel in their XML, 
                                # but setting a high value or 1.0/max usually works in STS.
                                v_data["fuel"] = 1000000.0 # Heuristic 'Full'
                                modified = True
                            # 3. Component Health
                            if "components" in v_data and isinstance(v_data["components"], dict):
                                for comp in v_data["components"].values():
                                    if isinstance(comp, dict) and "damage" in comp:
                                        comp["damage"] = 0
                                        modified = True
            
            if modified:
                updated = json.dumps(sts_json, separators=(',', ':'))
                self._write_atomic(sts_path, header + zlib.compress(updated.encode('utf-8')), manager=kwargs.get("manager"), tx_id=kwargs.get("tx_id"))
                
                if self._verify_integrity(sts_path, header):
                    mods.append(f"BINARY.REPAIR_REFUEL.{value}")
                else:
                    raise IOError(f"Post-write integrity check failed for {sts_path}")
        except Exception as e:
             print(f"[Mutator] repair error for {value}: {e}")

    def _action_binary_garage_vehicle(self, data, key, value, mods, region, **kwargs):
        """Relocates vehicle to garage in the specified region's STS file."""
        step = kwargs.get("step", {})
        target_file = step.get("target") or f"sts_level_{region.lower()}.cfg"
        sts_path = os.path.join(self.target_folder, target_file)
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
            # v110.32: Now using dictionary format for position
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
                self._write_atomic(sts_path, header + zlib.compress(updated.encode('utf-8')), manager=kwargs.get("manager"), tx_id=kwargs.get("tx_id"))
                
                if self._verify_integrity(sts_path, header):
                    mods.append(f"BINARY.GARAGE.{value}")
                else:
                    raise IOError(f"Post-write integrity check failed for {sts_path}")
        except Exception as e:
            print(f"[Mutator] garage error for {value}: {e}")

    def _action_binary_move_vehicle(self, data, key, value, mods, region, **kwargs):
        """Relocates vehicle to arbitrary coordinates in the specified region's STS file."""
        step = kwargs.get("step", {})
        target_file = step.get("target") or f"sts_level_{region.lower()}.cfg"
        sts_path = os.path.join(self.target_folder, target_file)
        if not os.path.exists(sts_path): return
        if not os.path.exists(sts_path): return
        
        # 'value' expected to be Dict[str, float] with x, y, z
        if not isinstance(value, dict) or "x" not in value:
            return

        try:
            with open(sts_path, 'rb') as f: raw = f.read()
            header = raw[:4]
            payload = zlib.decompress(raw[4:])
            sts_json = json.loads(payload.decode('utf-8', errors='replace'))
            
            modified = False
            target_vehicle_id = value.get("vehicle_id")
            new_pos = {"x": float(value["x"]), "y": float(value["y"]), "z": float(value["z"])}

            for k in ["trucks", "objects"]:
                if k in sts_json and isinstance(sts_json[k], dict):
                    for v_key, v_data in sts_json[k].items():
                        if target_vehicle_id in v_key or (isinstance(v_data, dict) and (v_data.get("type") == target_vehicle_id)):
                            if "position" in v_data:
                                v_data["position"] = new_pos
                                modified = True
            
            if modified:
                updated = json.dumps(sts_json, separators=(',', ':'))
                self._write_atomic(sts_path, header + zlib.compress(updated.encode('utf-8')), manager=kwargs.get("manager"), tx_id=kwargs.get("tx_id"))
                
                if self._verify_integrity(sts_path, header):
                    mods.append(f"BINARY.MOVE.{target_vehicle_id}.{new_pos}")
                else:
                    raise IOError(f"Post-write integrity check failed for {sts_path}")
        except Exception as e:
            print(f"[Mutator] move error for {target_vehicle_id}: {e}")

    def _action_binary_move_trailer(self, data, key, value, mods, region, **kwargs):
        """Relocates trailer to arbitrary coordinates in the specified region's STS file."""
        step = kwargs.get("step", {})
        target_file = step.get("target") or f"sts_level_{region.lower()}.cfg"
        sts_path = os.path.join(self.target_folder, target_file)
        if not os.path.exists(sts_path): return
        if not os.path.exists(sts_path): return
        
        if not isinstance(value, dict) or "x" not in value: return

        try:
            with open(sts_path, 'rb') as f: raw = f.read()
            header = raw[:4]
            payload = zlib.decompress(raw[4:])
            sts_json = json.loads(payload.decode('utf-8', errors='replace'))
            
            modified = False
            target_id = value.get("trailer_id")
            new_pos = {"x": float(value["x"]), "y": float(value["y"]), "z": float(value["z"])}

            if "trailers" in sts_json and isinstance(sts_json["trailers"], dict):
                # Deep Check: Existence
                found = False
                for t_key, t_data in sts_json["trailers"].items():
                    if target_id in t_key or (isinstance(t_data, dict) and (t_data.get("type") == target_id)):
                        if "position" in t_data:
                            t_data["position"] = new_pos
                            modified = True
                            found = True
                if not found:
                    print(f"[BinaryGuard] Trailer '{target_id}' not found in STS world.")
                    return
            
            if modified:
                updated = json.dumps(sts_json, separators=(',', ':'))
                self._write_atomic(sts_path, header + zlib.compress(updated.encode('utf-8')), manager=kwargs.get("manager"), tx_id=kwargs.get("tx_id"))
                
                if self._verify_integrity(sts_path, header):
                    mods.append(f"BINARY.MOVE_TRAILER.{target_id}")
                else:
                    raise IOError("Post-write integrity check failed")
        except Exception as e:
            print(f"[Mutator] trailer move error: {e}")

    def _action_binary_repair_trailer(self, data, key, value, mods, region, **kwargs):
        """Resets damage and refills tank for trailers."""
        step = kwargs.get("step", {})
        target_file = step.get("target") or f"sts_level_{region.lower()}.cfg"
        sts_path = os.path.join(self.target_folder, target_file)
        if not os.path.exists(sts_path): return
        if not os.path.exists(sts_path): return

        try:
            with open(sts_path, 'rb') as f: raw = f.read()
            header = raw[:4]
            payload = zlib.decompress(raw[4:])
            sts_json = json.loads(payload.decode('utf-8', errors='replace'))
            
            modified = False
            target_id = value # Trailer Type or ID

            if "trailers" in sts_json and isinstance(sts_json["trailers"], dict):
                for t_key, t_data in sts_json["trailers"].items():
                    if target_id in t_key or (isinstance(t_data, dict) and (t_data.get("type") == target_id)):
                        # 1. Reset Damage
                        if "damage" in t_data:
                            t_data["damage"] = 0
                            modified = True
                        # 2. Refill Tank (if applicable)
                        if "fuel" in t_data:
                            t_data["fuel"] = 1000000.0
                            modified = True
                        # 3. Components
                        if "components" in t_data and isinstance(t_data["components"], dict):
                            for comp in t_data["components"].values():
                                if isinstance(comp, dict) and "damage" in comp:
                                    comp["damage"] = 0
                                    modified = True
            
            if modified:
                updated = json.dumps(sts_json, separators=(',', ':'))
                self._write_atomic(sts_path, header + zlib.compress(updated.encode('utf-8')), manager=kwargs.get("manager"), tx_id=kwargs.get("tx_id"))
                
                if self._verify_integrity(sts_path, header):
                    mods.append(f"BINARY.REPAIR_TRAILER.{target_id}")
                else:
                    raise IOError("Post-write integrity check failed")
        except Exception as e:
            print(f"[Mutator] trailer repair error: {e}")

    def _action_binary_set_cargo(self, data, key, value, mods, region, **kwargs):
        """Manipulates truck/trailer cargo inventory with deep state validation."""
        step = kwargs.get("step", {})
        target_file = step.get("target") or f"sts_level_{region.lower()}.cfg"
        sts_path = os.path.join(self.target_folder, target_file)
        if not os.path.exists(sts_path): return
        
        if not isinstance(value, dict): return

        try:
            with open(sts_path, 'rb') as f: raw = f.read()
            header = raw[:4]
            payload = zlib.decompress(raw[4:])
            sts_json = json.loads(payload.decode('utf-8', errors='replace'))
            
            modified = False
            v_id = value.get("vehicle_id")
            c_id = value.get("cargo_id") # e.g. "CargoWoodenPlanks"
            op = value.get("op", "add")

            # Check trucks and trailers
            found_carrier = False
            for zone in ["trucks", "trailers", "objects"]:
                if zone in sts_json and isinstance(sts_json[zone], dict):
                    for v_key, v_data in sts_json[zone].items():
                        if v_id in v_key or (isinstance(v_data, dict) and (v_data.get("type") == v_id)):
                            found_carrier = True
                            # inventory block
                            if "inventory" not in v_data: v_data["inventory"] = []
                            if not isinstance(v_data["inventory"], list): v_data["inventory"] = []
                            
                            cargo_list = v_data["inventory"]

                            if op == "add":
                                # Deep Rule: Uniqueness
                                if c_id in cargo_list:
                                    print(f"[BinaryGuard] Cargo '{c_id}' already exists on '{v_id}'. Blocked.")
                                    return
                                
                                # Deep Rule: Capacity (Heuristic: 4 for trucks, 8 for trailers)
                                limit = 8 if zone == "trailers" else 4
                                if len(cargo_list) >= limit:
                                    print(f"[BinaryGuard] Capacity limit reached for '{v_id}'. Blocked.")
                                    return

                                cargo_list.append(c_id)
                                modified = True
                            elif op == "remove" and c_id in cargo_list:
                                cargo_list.remove(c_id)
                                modified = True
                            elif op == "clear":
                                v_data["inventory"] = []
                                modified = True
            
            if not found_carrier:
                print(f"[BinaryGuard] Carrier '{v_id}' not found in STS world.")
                return

            if modified:
                updated = json.dumps(sts_json, separators=(',', ':'))
                self._write_atomic(sts_path, header + zlib.compress(updated.encode('utf-8')), manager=kwargs.get("manager"), tx_id=kwargs.get("tx_id"))
                
                if self._verify_integrity(sts_path, header):
                    mods.append(f"BINARY.CARGO.{op}.{c_id}")
                else:
                    raise IOError("Post-write integrity check failed")
        except Exception as e:
            print(f"[Mutator] cargo modification error: {e}")

    def _action_binary_sts_upgrade_removal(self, data, key, value, mods, region, **kwargs):
        """Surgically removes upgrade markers from the STS world-state file."""
        step = kwargs.get("step", {})
        target_file = step.get("target") or f"sts_level_{region.lower()}.cfg"
        sts_path = os.path.join(self.target_folder, target_file)
        if not os.path.exists(sts_path): return
        
        try:
            with open(sts_path, 'rb') as f: raw = f.read()
            header = raw[:4]
            payload = zlib.decompress(raw[4:])
            sts_json = json.loads(payload.decode('utf-8', errors='replace'))
            
            modified = False
            # Upgrades are typically in "upgrades" or "upgrades_giver"
            for zone in ["upgrades", "upgrades_giver"]:
                if zone in sts_json and isinstance(sts_json[zone], dict):
                    to_delete = []
                    for upg_key, upg_data in sts_json[zone].items():
                        if value in upg_key or (isinstance(upg_data, dict) and upg_data.get("type") == value):
                            to_delete.append(upg_key)
                    
                    for k in to_delete:
                        del sts_json[zone][k]
                        modified = True
                        mods.append(f"BINARY.UPGRADE_REMOVAL.{value}")
            
            if modified:
                updated = json.dumps(sts_json, separators=(',', ':'))
                self._write_atomic(sts_path, header + zlib.compress(updated.encode('utf-8')), manager=kwargs.get("manager"), tx_id=kwargs.get("tx_id"))
                
                if self._verify_integrity(sts_path, header):
                    pass
                else:
                    raise IOError("Post-write integrity check failed")
        except Exception as e:
            print(f"[Mutator] upgrade removal error: {e}")

    # --- Phase 14: Objectives+ Linkage Handlers ---

    def _action_mark_finished(self, data, key, value, mods, region, **kwargs):
        """Updates SslValue.finishedObjs in CompleteSave. Handles both list and dict formats."""
        if not data or not value: return
        
        # Traverse to SslValue
        ssl = data.get("SslValue", {})
        if not ssl: return

        finished = ssl.get("finishedObjs")
        if finished is None:
            finished = []
        
        modified = False
        if isinstance(finished, list):
            if value not in finished:
                finished.append(value)
                modified = True
        elif isinstance(finished, dict):
            if value not in finished:
                finished[value] = True
                modified = True
        
        if modified:
            ssl["finishedObjs"] = finished
            data["SslValue"] = ssl
            mods.append(f"JSON.OBJECTIVE.MARK_FINISHED.{value}")

    def _action_accept_objective(self, data, key, value, mods, region, **kwargs):
        """Sets 'isAccepted': true in objectiveStates block if not already."""
        if not data or not value: return
        
        states = data.get("objectiveStates", {})
        if not isinstance(states, dict):
            states = {}
            data["objectiveStates"] = states

        obj_id = str(value)
        current = states.get(obj_id, {})
        if not isinstance(current, dict):
            current = {}
        
        if not current.get("isAccepted"):
            current["isAccepted"] = True
            states[obj_id] = current
            mods.append(f"JSON.OBJECTIVE.ACCEPTED.{obj_id}")

    def _action_update_objective_state(self, data, key, value, mods, region, **kwargs):
        """Sets 'isFinished': true in objectiveStates block."""
        if not data or not value: return
        
        states = data.get("objectiveStates", {})
        if not isinstance(states, dict):
            states = {}
            data["objectiveStates"] = states

        obj_id = str(value)
        current = states.get(obj_id, {})
        if not isinstance(current, dict):
            current = {}
        
        if not current.get("isFinished"):
            current["isFinished"] = True
            current["lastStatus"] = 3  # 3 = Finished/Completed in SnowRunner engine
            current["isAccepted"] = True
            # Sub-objectives are often handled by the engine seeing isFinished, 
            # but setting lastStatus ensures the 'Checkmark' UI is solid.
            states[obj_id] = current
            mods.append(f"JSON.OBJECTIVE.STATE_FINISHED.{obj_id}")

    def _action_remove_objective_state(self, data, key, value, mods, region, **kwargs):
        """Removes an entry from objectiveStates (for resets)."""
        if not data or not value: return
        
        states = data.get("objectiveStates", {})
        if isinstance(states, dict) and value in states:
            del states[value]
            mods.append(f"JSON.OBJECTIVE.STATE_REMOVED.{value}")

    def _action_apply_objective_rewards(self, data, key, value, mods, region, **kwargs):
        """Dynamically applies Money and XP rewards based on mission ID and resolver metadata."""
        if not data or not value: return
        
        # 0. RESOLVER METADATA OVERRIDE (v110.43 Preference)
        # We prefer the hard-coded rewards in OBJECTIVE_METADATA for accuracy.
        manager = kwargs.get("manager")
        resolver = manager.resolver if manager else None
        meta_rewards = None
        if resolver and hasattr(resolver, "OBJECTIVE_METADATA"):
             meta = resolver.OBJECTIVE_METADATA.get(value)
             if meta: meta_rewards = meta.get("rewards")

        if meta_rewards:
            money_add = meta_rewards.get("money", 0)
            xp_add = meta_rewards.get("xp", 0)
        else:
            # Fallback to scraped database
            db = get_objective_db()
            rewards = db.get_rewards(value) if hasattr(db, "get_rewards") else {}
            money_add = rewards.get("money", 0) if rewards else 0
            xp_add = rewards.get("xp", 0) if rewards else 0

        if money_add <= 0 and xp_add <= 0:
            return

        # ⚠️ Duplication Guard: Check if already completed in states
        # The states block is the 'Source of Truth' for completion rewards
        states = data.get("objectiveStates", {})
        if isinstance(states, dict) and states.get(value, {}).get("isFinished"):
            # Already rewarding; skip to prevent exploits
            return

        # SslValue update
        ssl = data.get("SslValue", {})
        if not ssl: return

        modified = False
        if money_add > 0:
            current_money = int(ssl.get("money", 0))
            ssl["money"] = current_money + money_add
            mods.append(f"JSON.REWARD.MONEY.+{money_add}")
            modified = True
        
        if xp_add > 0:
            current_xp = int(ssl.get("experience", 0))
            
            # [v110.43] Early Exit if already at or above cap
            if current_xp >= self.MAX_XP_LEVEL_30:
                mods.append(f"JSON.REWARD.XP.SKIPPED.ALREADY_CAPPED")
            else:
                new_xp = min(current_xp + xp_add, self.MAX_XP_LEVEL_30)
                
                if new_xp == self.MAX_XP_LEVEL_30:
                    mods.append(f"JSON.REWARD.XP.+{xp_add}.CAPPED_LEVEL_30")
                else:
                    mods.append(f"JSON.REWARD.XP.+{xp_add}")
                
                ssl["experience"] = new_xp
                data["SslValue"] = ssl
                modified = True

    def _action_sync_global_objective(self, data, key, value, mods, region, **kwargs):
        """Pairs with CommonSslSave for global achievement counters."""
        if not data or not value: return
        # CommonSslSave often mirrors the 'finishedObjs' list or uses 'finishedTasks'
        # We ensure the objective_id is in the top-level 'finishedObjs' list of CommonSslSave.
        finished = data.get("finishedObjs")
        if isinstance(finished, list) and value not in finished:
            finished.append(value)
            mods.append(f"JSON.GLOBAL_SYNC.OBJECTIVE.{value}")
        elif isinstance(finished, dict) and value not in finished:
            finished[value] = True
            mods.append(f"JSON.GLOBAL_SYNC.OBJECTIVE.{value}")

    def _action_binary_sts_objective_sync(self, data, key, value, mods, region, **kwargs):
        """
        [v110.43] Critical World-State Sync: 
        Finds the marker/zone in the binary STS file and marks it as completed.
        This triggers the visual clearing of rockfalls/bridges.
        """
        manager = kwargs.get("manager")
        if not manager: return
        resolver = manager.resolver
        meta = resolver.OBJECTIVE_METADATA.get(value)
        if not meta or not meta.get("affects_world"): return
        
        marker_id = meta.get("marker_id")
        map_id = meta.get("map")
        
        # We are INSIDE a linkage handler for an STS file.
        # The 'data' passed to us is the JSON content of the STS file (due to apply_global_linkage).
        # We find and modify the marker in this 'data' block.
        
        modified = False
        # Bridges/Rockfalls are typically in 'zone_states' or 'objects' or 'upgrades'
        # Depending on the specific map structure.
        for zone_key in ["zone_states", "objects", "upgrades"]:
            if zone_key in data and isinstance(data[zone_key], dict):
                # Search for the marker ID
                found_key = None
                for k in data[zone_key]:
                    if marker_id in k:
                         found_key = k; break
                
                if found_key:
                    target = data[zone_key][found_key]
                    if isinstance(target, dict):
                        target["isCompleted"] = True
                        target["state"] = 1 # 1 = Completed/Revealed/Cleared
                        if "isRevealed" in target: target["isRevealed"] = True
                        modified = True
                        mods.append(f"BINARY.STS_SYNC.{marker_id}.SUCCESS")
                        
                        # [v110.43] Immediate Structural Assertion
                        assert target.get("state") == 1, f"STS state memory corruption for {marker_id}"
                        break
        
        if not modified:
             raise ValueError(f"CRITICAL: STS marker '{marker_id}' not found in world-state for objective '{value}'. Save version mismatch suspected.")

    def _action_batch_apply_rewards(self, data, key, value, mods, region, **kwargs):
        """[v110.43] Applies pre-aggregated Money and XP rewards for a batch of objectives."""
        if not data or not isinstance(value, dict): return
        
        total_money = value.get("money", 0)
        total_xp = value.get("xp", 0)
        
        ssl = data.get("SslValue", {})
        if not ssl: return
        
        if total_money > 0:
            ssl["money"] = int(ssl.get("money", 0)) + total_money
            mods.append(f"JSON.REWARD.BATCH_MONEY.+{total_money}")
            
        if total_xp > 0:
            current_xp = int(ssl.get("experience", 0))
            if current_xp >= self.MAX_XP_LEVEL_30:
                mods.append("JSON.REWARD.BATCH_XP.SKIPPED.ALREADY_CAPPED")
            else:
                new_xp = min(current_xp + total_xp, self.MAX_XP_LEVEL_30)
                ssl["experience"] = new_xp
                mods.append(f"JSON.REWARD.BATCH_XP.+{total_xp}.FINAL_XP={new_xp}")

    def _action_batch_sts_sync(self, data, key, value, mods, region, **kwargs):
        """[v110.43] Marks multiple markers as completed in a single STS file cycle."""
        if not data or not isinstance(value, list): return
        
        found_markers = []
        for marker_id in value:
            success = False
            for zone_key in ["zone_states", "objects", "upgrades"]:
                if zone_key in data and isinstance(data[zone_key], dict):
                    found_key = None
                    for k in data[zone_key]:
                        if marker_id in k:
                            found_key = k; break
                    if found_key:
                        target = data[zone_key][found_key]
                        target["isCompleted"] = True
                        target["state"] = 1
                        if "isRevealed" in target: target["isRevealed"] = True
                        found_markers.append(marker_id)
                        success = True
                        break
            if not success:
                raise ValueError(f"CRITICAL: Batch STS marker '{marker_id}' not found in data.")
        
        mods.append(f"BINARY.BATCH_STS_SYNC.{len(found_markers)}_MARKERS")
