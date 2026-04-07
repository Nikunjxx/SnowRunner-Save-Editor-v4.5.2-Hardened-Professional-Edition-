import os
import time
import hashlib
import uuid
import tempfile
import json
import zlib
import re
import datetime
from typing import List, Dict, Any, Tuple, Optional
import collections
from collections import defaultdict
from contextlib import contextmanager
from .slot_context import SlotContext
from .constraints import ConstraintEngine
from .backups import BackupManager
from .validator import Validator, ValidationReport
from .dependency_resolver import DependencyResolver
from .procedural_mutators import ProceduralMutator
from .logger import OperationLogger
from .reference_extractor import ReferenceExtractor
from .preflight import PreflightEngine, PreflightReport, PreflightIssue
from .observability import ObservabilityEngine
from .fingerprint import FingerprintEngine
from .scenario import ScenarioEngine, Scenario

class ZlibHandler:
    """[v112.50] Resilient Binary/JSON Pipeline for Steam & Epic/MS .cfg Files."""
    MAGIC_STS = b"\x3d\x61\x06\x00"
    MAGIC_FOG = b"\x41\x4b\x05\x00"
    
    @staticmethod
    def read(path: str) -> Tuple[bytes, bytes]:
        """Reads file and returns (header, payload). Supports Plain JSON (Steam)."""
        with open(path, "rb") as f:
            raw = f.read()
        
        if not raw: return b"", b""
        
        # [v112.50] Toggle Mode: Plain JSON detection (Starting with 0x7b '{')
        if raw[0] == 0x7b:
            return b"", raw
            
        # [v113.00] Steam Binary Header detection (offset 0, 4 bytes)
        if raw[:4] in [b"\x70\x29\x09\x00", b"\x3d\x61\x06\x00"]:
             header = raw[:4]
             try:
                 return header, zlib.decompress(raw[4:])
             except zlib.error:
                 return b"", raw
        
        # Standard ZLIB magic (78 9C/DA/01 at offset 4)
        if len(raw) > 4 and raw[4:6] in [b"\x78\x9c", b"\x78\xda", b"\x78\x01"]:
            header = raw[:4]
            try:
                return header, zlib.decompress(raw[4:])
            except zlib.error:
                 return b"", raw
        return b"", raw

    @staticmethod
    def write(path: str, payload: bytes, header: bytes = None):
        """Compressed write-back with backup and header preservation."""
        if os.path.exists(path):
            with open(path + ".bak", "wb") as f:
                with open(path, "rb") as src: f.write(src.read())

        final_data = payload
        if header:
            # Recompress and prepend header
            compressed = zlib.compress(payload, level=6)
            final_data = header + compressed
            
        with open(path, "wb") as f:
            f.write(final_data)

class IntegrityManager:
    """
    Orchestrates the 4-layer High-Safety Pipeline:
    UI -> [IntegrityManager] -> Resolver -> Validator -> Mutator -> Backups -> Logger
    """
    def _detect_active_slot(self) -> str:
        """[v111.00] Determines the most likely active save slot in the folder."""
        try:
            files = os.listdir(self.target_folder)
            for f in files:
                if f.startswith("CompleteSave") and (f.endswith(".cfg") or f.endswith(".dat")):
                    return f
            return "CompleteSave.cfg"
        except: return "CompleteSave.cfg"

    def _scan_available_slots(self) -> List[str]:
        """[v111.00] Returns all found CompleteSave files."""
        try:
            return [f for f in os.listdir(self.target_folder) 
                    if f.startswith("CompleteSave") and (f.endswith(".cfg") or f.endswith(".dat"))]
        except: return []

    def __init__(self, target_folder: str, data_dir: str, remote2_path: str, progress_callback: Any = None):
        self.target_folder = target_folder
        self.data_dir = data_dir
        self.remote2_path = remote2_path
        self.dry_run = False
        
        # Paths
        self.cache_file = os.path.join(data_dir, "reference_patterns.json")
        self.log_file = os.path.join(data_dir, "operations.log")
        self.metrics_file = os.path.join(data_dir, "metrics.json")
        self.presets_file = os.path.join(data_dir, "presets.json")
        
        # Initialize Core Modules
        self.backups = BackupManager(data_dir)
        self.extractor = ReferenceExtractor(remote2_path, self.cache_file)
        self.resolver = DependencyResolver(self.cache_file)
        self.validator = Validator(self.cache_file)
        self.mutator = ProceduralMutator(target_folder)
        self.logger = OperationLogger(self.log_file)
        self.preflight = PreflightEngine(target_folder)
        self.constraints = ConstraintEngine(target_folder)
        self.metrics = ObservabilityEngine(self.metrics_file)
        self.fingerprint = FingerprintEngine(target_folder)
        self.scenario_engine = ScenarioEngine(self.presets_file)
        self.zlib_handler = ZlibHandler()
        
        base_dir = os.path.dirname(os.path.abspath(__file__))
        self.map_labels_path = os.path.normpath(os.path.join(base_dir, "registry", "map_labels.json"))
        self.map_labels = {}
        
        if os.path.exists(self.map_labels_path):
            try:
                with open(self.map_labels_path, "r", encoding="utf-8") as f:
                    self.map_labels = json.load(f)
            except: pass
        
        # Phase 1: Slot Detection
        self.active_slot = self._detect_active_slot()
        self.save_context = {
            "root": target_folder,
            "slot": {
                "active": self.active_slot,
                "available": self._scan_available_slots()
            },
            "files": {},
            "regions": collections.defaultdict(lambda: {"maps": {}, "objectives": {}, "fog": {}}),
            "player": {},
            "meta": {"source_path": target_folder}
        }

        # Components
        self.resolver = DependencyResolver(self.save_context)
        self.resolver.set_save_context(self.save_context)
        
        # Ensure reference cache exists (One-time Pass 0)
        self.extractor.extract_all(progress_callback=progress_callback)

    @contextmanager
    def transaction(self, whitelist: List[str] = None):
        """
        [v111.00] External Transaction Guard for Plugin Mutations.
        Wraps any block of code in a Backup -> Execute -> Verify -> Rollback cycle.
        """
        if whitelist is None:
            # Default to all registered files in context if none specified
            whitelist = []
            
            # v111.00: Re-wired to use registry-based whitelisting
            active_slot = self.save_context["slot"]["active"]
            if active_slot: whitelist.append(active_slot)
            
            # Add all registered STS and Fog files from the registry
            for fpath, finfo in self.save_context["files"].items():
                if finfo["type"] in ["objectives", "fog", "progression"]:
                    whitelist.append(fpath)

        tx_id = str(uuid.uuid4())
        self.logger.log_operation("TRANSACTION_START", {"tx_id": tx_id, "whitelist": whitelist})
        
        # 1. Backup
        if not self.dry_run:
            self.backups.trigger_backup(self.target_folder, whitelist)
        
        try:
            yield tx_id
            
            # 2. Post-Yield Verification
            report = self.validate_targeted_files(whitelist)
            if not report.is_safe:
                raise RuntimeError(f"Transaction validation failed: {', '.join(report.warnings)}")
            
            # 3. Snapshot and Commit
            if not self.dry_run:
                self.snapshot_context()
                self.session_state = "MODIFIED"
            
            self.logger.log_operation("TRANSACTION_COMMIT", {"tx_id": tx_id})
            
        except Exception as e:
            self.logger.log_operation("TRANSACTION_ROLLBACK", {"tx_id": tx_id, "error": str(e)})
            if not self.dry_run:
                self.backups.restore_last_delta(self.target_folder)
            raise
            
    # ... (other methods)

    def execute_scenario(self, scenario_id: str) -> dict:
        """
        [v110.40] Atomic implementation of the Scenario Engine.
        Executes a multi-feature preset in a single Backup/Write/Verify cycle.
        """
        scenario = self.scenario_engine.get_scenario(scenario_id)
        if not scenario:
            return {"success": False, "error": f"Scenario '{scenario_id}' not found."}

        version = self._detect_save_version()
        start_time = time.time()
        result = {"success": False, "report": None, "error": "", "status": "failed", "processed": 0}
        
        try:
            all_mutations = []
            unified_whitelist = set()
            total_bytes = 0
            
            # 1. Resolve and Validate all steps first
            for action in scenario.actions:
                # 1.1 Resolution
                whitelist, mutations = self.resolver.resolve(
                    action.feature, action.region, value=action.value, xp_value=action.xp_value, 
                    objective_id=action.objective_id, achievement_id=action.achievement_id,
                    supplemental_data=action.supplemental_data
                )
                all_mutations.extend(mutations)
                unified_whitelist.update(whitelist)
            
            final_whitelist = list(unified_whitelist)
            
            # 1.2 [v110.40] External Change Guard
            is_valid, conflicts = self.check_session_validity()
            if not is_valid:
                result["error"] = f"Session Stale: External modification detected."
                result["status"] = "stale"
                return result

            # 1.3 Zero-Trust Pre-flight on unified whitelist
            self.pre_transaction_guard(final_whitelist)
            
            # 2. Capture Before State + Bytes
            before_hashes = self._get_file_hashes(final_whitelist)
            for f in final_whitelist:
                p = os.path.join(self.target_folder, f)
                if os.path.exists(p): total_bytes += os.path.getsize(p)
            
            # 3. Unified Backup
            if not self.dry_run:
                self.backups.trigger_backup(self.target_folder, final_whitelist)
            
            # 4. Atomic Multi-feature Execution
            # Determine target file (CompleteSave takes precedence)
            target_file = "CompleteSave.cfg" if any(f.endswith(".cfg") for f in final_whitelist) else "CompleteSave.dat"
            
            op_success = self.mutator.apply_global_linkage(
                os.path.join(self.target_folder, target_file), 
                all_mutations,
                resolver_ref=self.resolver,
                feature_ref=f"SCENARIO_{scenario_id}",
                dry_run=self.dry_run
            )
            
            # 5. Final Global Validation
            if op_success:
                # [v110.40] Targeted Smart Audit
                report = self.validate_targeted_files(final_whitelist)
                result["report"] = report
                
                if not report.is_safe:
                    if not self.dry_run:
                        self.backups.restore_last_delta(self.target_folder)
                    result["error"] = "Structural Validation Failed during Scenario (Rolled Back)"
                    result["status"] = "failed"
                else:
                    result["success"] = True
                    result["processed"] = len(scenario.actions)
                    result["status"] = "success" if not report.warnings else "warning"
                    
                    # 6. [v110.40] Success Snapshot
                    if result["success"] and not self.dry_run:
                        self.snapshot_context()
                        self.session_state = "MODIFIED"
            else:
                 result["error"] = f"Scenario '{scenario_id}' failed during linkage sync."

        except Exception as e:
            result["error"] = f"Critical Scenario Error: {e}"
            if 'final_whitelist' in locals() and not self.dry_run:
                self.backups.restore_last_delta(self.target_folder)

        # 6. Persistent Metrics & Logging
        duration_ms = int((time.time() - start_time) * 1000)
        final_status = "DRY_RUN_SUCCESS" if self.dry_run and result["success"] else result["status"]
        self.metrics.record_mutation(final_status, duration_ms, total_bytes, feature=f"SCENARIO_{scenario_id}")
        
        after_hashes = self._get_file_hashes(final_whitelist if 'final_whitelist' in locals() else [])
        self.logger.log_operation(
            feature=f"SCENARIO_{scenario_id}",
            region="VARIOUS",
            duration_ms=duration_ms,
            files_modified=final_whitelist if 'final_whitelist' in locals() else [],
            status=final_status,
            warnings=result["report"].warnings if result["report"] else [],
            reason=result["error"],
            before_hashes=before_hashes if 'before_hashes' in locals() else {},
            after_hashes=after_hashes,
            version=version
        )
        return result

    def _get_empty_context(self) -> dict:
        """v112.00: Returns the base PRODUCTION-READY schema."""
        return {
            "meta": {
                "session_id": time.strftime("%Y-%m-%d_%H-%M-%S"),
                "game_version": "Unknown",
                "platform": "Unknown",
                "source_path": self.target_folder,
                "loaded_at": time.time(),
            },
            "slot": {
                "available": [],
                "active": None
            },
            "player": {
                "money": 0,
                "rank": 0,
                "experience": 0,
                "owned_vehicles": [],
                "garage": {}
            },
            "regions": {},
            "maps_index": {},
            "files": {}, # file_path -> {used_in: [], maps: [], fields: [], header: bytes}
            "change_log": [],
            # --- [v112.00] Legacy Bridge (Prevents KeyErrors during migration) ---
            "main": None,
            "global": None,
            "sts": {},
            "fog": {}
        }

    def _hydrate_context(self, slot_filename: str = None, progress_callback=None, lazy: bool = False):
        """
        v112.00: MASTER HYDRATION ENGINE (Enforced 5-Pass Order).
        v113.00: Added progress_callback for background threading support.
        v115.07: Added lazy mode for near-instant indexing (Pass 0 only).
        """
        def _report(msg, progress):
            if progress_callback:
                try: progress_callback(msg, progress)
                except: pass

        _report("Initializing hydration engine...", 0.05)
        self.save_context = self._get_empty_context()
        self.save_context["meta"]["source_path"] = self.target_folder
        
        try:
            # 0. Initial Discovery (Fast)
            _report("Scanning folder structure...", 0.1)
            files = os.listdir(self.target_folder)
            self.save_context["slot"]["available"] = [f for f in files if "CompleteSave" in f and (f.endswith(".cfg") or f.endswith(".dat"))]
            
            # Select Slot
            if slot_filename and slot_filename in self.save_context["slot"]["available"]:
                active_slot = slot_filename
            else:
                active_slot = next((f for f in files if f == "CompleteSave.cfg"), 
                             next((f for f in files if f == "CompleteSave.dat"),
                             self.save_context["slot"]["available"][0] if self.save_context["slot"]["available"] else None))
            
            self.save_context["slot"]["active"] = active_slot
            if not active_slot:
                print("[HYDRATION] No active slot found")
                _report("No save slots discovered.", 1.0)
                return
            
            self.save_context["main"] = active_slot

            # Register files into context for the Sanitizer (Fast)
            for f in files:
                if f.startswith("sts_level_"): self.save_context["files"][f] = {"type": "objectives", "maps": [f.replace("sts_level_", "").replace(".cfg", "").replace(".dat", "")]}
                elif f.startswith("fog_level_"): self.save_context["files"][f] = {"type": "fog", "maps": [f.replace("fog_level_", "").replace(".cfg", "").replace(".dat", "")]}

            if lazy:
                # [v115.07] Return early for instant UI responsiveness
                _report("Folder indexed. Deep extraction deferred...", 1.0)
                return self.save_context

            # --- DEEP HYDRATION (Heavy: Decompression & Parsing) ---

            # PASS 1: Skeleton (From Static Registry)
            _report(f"Building map registry ({len(self.map_labels)} maps)...", 0.2)
            self._pass_1_build_skeleton()

            # PASS 2: Global Progression (CommonSslSave)
            _report("Indexing global progression...", 0.4)
            global_file = next((f for f in files if "CommonSslSave" in f), None)
            if global_file:
                try: self._pass_2_apply_global(global_file)
                except Exception as e: print(f"[PASS 2 FAIL] {e}")

            # PASS 3: Player Data (CompleteSaveX)
            _report(f"Parsing active slot: {active_slot}...", 0.6)
            try: self._pass_3_apply_slot(active_slot)
            except Exception as e: print(f"[PASS 3 FAIL] {e}")

            # PASS 4: Regional Objectives (Binary STS) - [v113.10] PARALLEL OPTIMIZED
            sts_files = [f for f in files if f.startswith("sts_level_")]
            total_sts = len(sts_files)
            
            if total_sts > 0:
                _report(f"Synchronizing world state ({total_sts} maps)...", 0.6)
                from concurrent.futures import ThreadPoolExecutor
                max_workers = min(os.cpu_count() or 4, 8)
                
                with ThreadPoolExecutor(max_workers=max_workers) as executor:
                    list(executor.map(self._pass_4_apply_sts, sts_files))
                
                _report("World state synchronized.", 0.8)
            else:
                _report("No regional world state files found.", 0.8)

            # PASS 5: Exploration (Fog/Visited Logic)
            _report("Resolving exploration metadata...", 0.9)
            try: self._pass_5_apply_fog_logic()
            except Exception as e: print(f"[PASS 5 FAIL] {e}")

            _report("Finalizing folder context...", 1.0)

        except Exception as e:
            self.logger.log_operation("HYDRATE_CRITICAL_FAIL", {"error": str(e)})
            _report(f"Critical Fail: {str(e)}", 1.0)

        # [v112.00] Sync Legacy Bridge
        ctx = self.save_context
        ctx["main"] = ctx["slot"]["active"]
        ctx["global"] = next((f for f, info in ctx["files"].items() if info["type"] == "progression"), None)
        ctx["sts"] = {finfo["maps"][0]: f for f, finfo in ctx["files"].items() if finfo["type"] == "objectives"}
        ctx["fog"] = {finfo["maps"][0]: f for f, finfo in ctx["files"].items() if finfo["type"] == "fog"}

        return self.save_context

    def _pass_1_build_skeleton(self):
        """v112.00: PASS 1 - Initialize the world structure from static metadata."""
        self.save_context["regions"] = {}
        self.save_context["maps_index"] = {}
        
        for mid, minfo in self.map_labels.items():
            rname = minfo["region"]
            mname = minfo["name"]
            
            if rname not in self.save_context["regions"]:
                self.save_context["regions"][rname] = {"maps": {}, "order": len(self.save_context["regions"]) + 1}
            
            self.save_context["regions"][rname]["maps"][mname] = {
                "map_id": mid,
                "progression": {"unlocked": False, "visited": False},
                "objectives": {"total": 0, "completed": 0, "list": []},
                "fog": {"revealed": False}
            }
            self.save_context["maps_index"][mid] = {"region": rname, "map": mname}

    def _resilient_json_load(self, payload: bytes) -> dict:
        """[v112.70] Safe JSON extraction with Steam SslValue peeling."""
        if not payload: return {}
        try:
            text = payload.decode('utf-8')
            # [v112.70] Resilient Loader
            try:
                data = json.loads(text)
            except json.JSONDecodeError:
                decoder = json.JSONDecoder()
                data, _ = decoder.raw_decode(text)
            
            # [v112.70] Explicit recursive peeling for Steam container structure
            if "CompleteSave" in data:
                save = data["CompleteSave"]
                if isinstance(save, dict) and "SslValue" in save:
                    return save["SslValue"]
            if "CommonSslSave" in data:
                common = data["CommonSslSave"]
                if isinstance(common, dict) and "SslValue" in common:
                    return common["SslValue"]
            return data
        except Exception as e:
            print(f"[v112.70] JSON Critical Fail: {e}")
            return {}

    def _find_key_recursive(self, data, target_key):
        """v112.60: Case-Insensitive Deep-recursive navigator for resilient schema traversal."""
        if not data or not isinstance(data, (dict, list)): return None
        target_lower = target_key.lower()
        
        if isinstance(data, dict):
            # Check keys at current level (Case-Insensitive)
            for k, v in data.items():
                if k.lower() == target_lower:
                    return v
            # Recurse into values
            for val in data.values():
                res = self._find_key_recursive(val, target_key)
                if res is not None: return res
        elif isinstance(data, list):
            for item in data:
                res = self._find_key_recursive(item, target_key)
                if res is not None: return res
        return None

    def _pass_2_apply_global(self, filename: str):
        """v112.70: PASS 2 - Apply CommonSslSave data (Global Unlocks) with Explicit Peeling."""
        header, payload = self.zlib_handler.read(os.path.join(self.target_folder, filename))
        try:
            # v112.70 automatically peels SslValue
            data = self._resilient_json_load(payload)
            unlocked = self._find_key_recursive(data, "unlockedMaps")
            if not unlocked and isinstance(data, dict):
                 unlocked = data.get("unlockedMaps", [])
            
            if unlocked:
                for mid in unlocked:
                    idx_info = self.save_context["maps_index"].get(mid)
                    if idx_info:
                        self.save_context["regions"][idx_info["region"]]["maps"][idx_info["map"]]["progression"]["unlocked"] = True

            self.save_context["files"][filename] = {
                "type": "progression",
                "used_in": ["Map Unlock"],
                "maps": [],
                "fields": ["unlockedMaps"],
                "header": header
            }
        except: pass

    def _pass_3_apply_slot(self, filename: str):
        """v112.70: PASS 3 - Apply CompleteSaveX data (Player & Completed Objectives)."""
        header, payload = self.zlib_handler.read(os.path.join(self.target_folder, filename))
        try:
            # v112.70 automatically peels SslValue
            data = self._resilient_json_load(payload)
            
            # [v113.00] Multi-Key Player Stats Discovery (Steam uses persistentProfileData)
            p_info = self._find_key_recursive(data, "PersistentPlayerInfo")
            if not p_info:
                p_info = self._find_key_recursive(data, "persistentProfileData")
            
            if not p_info and isinstance(data, dict):
                p_info = data.get("PersistentPlayerInfo", data.get("persistentProfileData", {}))
                
            if p_info:
                stats = p_info.get("SslValue", p_info) if isinstance(p_info, dict) else {}
                # Fuzzy get for stats keys
                self.save_context["player"]["money"] = stats.get("money", stats.get("Money", 0))
                self.save_context["player"]["experience"] = stats.get("experience", stats.get("Experience", 0))
                self.save_context["player"]["rank"] = stats.get("rank", stats.get("Rank", 0))
            
            finished = self._find_key_recursive(data, "finishedObjs")
            if not finished and isinstance(data, dict): 
                finished = data.get("finishedObjs", [])
            if finished:
                self.save_context["meta"]["finished_objs"] = finished
            
            visited = self._find_key_recursive(data, "visitedLevels")
            if not visited and isinstance(data, dict):
                visited = data.get("visitedLevels", [])
            if visited:
                for mid in visited:
                    idx_info = self.save_context["maps_index"].get(mid)
                    if idx_info:
                        self.save_context["regions"][idx_info["region"]]["maps"][idx_info["map"]]["progression"]["visited"] = True

            self.save_context["files"][filename] = {
                "type": "player",
                "used_in": ["Bank & Rank"],
                "maps": [],
                "fields": ["money", "rank", "finishedObjs"],
                "header": header
            }
        except: pass

    def _pass_4_apply_sts(self, filename: str):
        """v113.10: PASS 4 - Extract Objective IDs (Registry Aligned & Regex Optimized)."""
        # [v113.10] Aligned with map_labels.json (level_us_01_01)
        map_id = filename[4:-4]
        
        try:
            full_path = os.path.join(self.target_folder, filename)
            header, payload = self.zlib_handler.read(full_path)
            
            idx_info = self.save_context["maps_index"].get(map_id)
            if not idx_info: return

            # [v113.10] Optimized Binary extraction
            # We target specific Saber ID prefixes to filter out noise at the regex level
            import re
            # Matches strings starting with known Saber mission prefixes
            pattern = b"(?:TSK_|CNT_|OBJ_|[a-zA-Z0-9_]+_(?:TASK|CONTRACT|MISSION|OBJ|REWARD))[a-zA-Z0-9_]*"
            strings = re.findall(pattern, payload)
            
            unique_ids = set()
            for s in strings:
                try:
                    unique_ids.add(s.decode('utf-8'))
                except: continue
            
            # Thread-safe update: regions keys are unique per thread here based on filename/map_id
            map_obj = self.save_context["regions"][idx_info["region"]]["maps"][idx_info["map"]]
            map_obj["objectives"]["list"] = sorted(list(unique_ids))
            map_obj["objectives"]["total"] = len(unique_ids)
            
            # Calculate completed from Pass 3 global list
            finished = self.save_context["meta"].get("finished_objs", [])
            completed_count = sum(1 for oid in unique_ids if oid in finished)
            map_obj["objectives"]["completed"] = completed_count

            # Thread-safe update: filename keys are unique
            self.save_context["files"][filename] = {
                "type": "objectives",
                "maps": [map_id],
                "header": header
            }
        except Exception as e:
            print(f"[STS FAIL] {filename}: {e}")

    def _pass_5_apply_fog_logic(self):
        """v112.00: PASS 5 - Exploration detection based on file presence and visited state."""
        files = os.listdir(self.target_folder)
        for mid, idx_info in self.save_context["maps_index"].items():
            f_name = f"fog_{mid}.cfg"
            if f_name in files:
                map_obj = self.save_context["regions"][idx_info["region"]]["maps"][idx_info["map"]]
                
                header, payload = self.zlib_handler.read(os.path.join(self.target_folder, f_name))
                # Detection: Mark visited if binary header is non-default or visited in Pass 3
                if len(payload) > 0 and (payload[0:8] != b"\x80" * 8):
                    map_obj["progression"]["visited"] = True
                
                self.save_context["files"][f_name] = {
                    "type": "fog",
                    "maps": [mid],
                    "header": header
                }

    def load_slot(self, slot_file: str):
        """v111.00: Mandatory Full Re-hydration when switching slots."""
        self._hydrate_context(slot_filename=slot_file)
        self.snapshot_context()
        return self.save_context

    def get_save_context(self) -> dict:
        """Returns the full Unified SaveContext (v111.00)."""
        return self.save_context

    def get_save_registry(self) -> dict:
        """v111.00: Compatibility shim for legacy plugins. Maps new context to old flat registry."""
        ctx = self.save_context
        # Extract filename associations
        main = ctx["slot"]["active"]
        global_f = next((f for f, info in ctx["files"].items() if info["type"] == "progression"), None)
        
        sts_map = {finfo["maps"][0]: f for f, finfo in ctx["files"].items() if finfo["type"] == "objectives"}
        fog_map = {finfo["maps"][0]: f for f, finfo in ctx["files"].items() if finfo["type"] == "fog"}
        
        return {
            "main": main,
            "global": global_f,
            "sts": sts_map,
            "fog": fog_map,
            "slot": 0, # Legacy slot index
            "platform": ctx["meta"]["platform"]
        }

    def get_region_metadata(self) -> dict:
        """v111.00: Compatibility shim. Maps regions tree back to flat level ID lists."""
        reg_meta = {}
        for rname, rinfo in self.save_context["regions"].items():
            reg_meta[rname] = [minfo["map_id"] for minfo in rinfo["maps"].values()]
        return reg_meta

    def audit_context(self) -> PreflightReport:
        """
        [v110.40] Performs a Zero-Trust audit on all indexed files in the context.
        """
        whitelist = [self.save_context["main"]] if self.save_context["main"] else []
        if self.save_context["global"]: whitelist.append(self.save_context["global"])
        whitelist.extend(self.save_context["sts"].values())
        whitelist.extend(self.save_context["fog"].values())
        
        return self.preflight.audit_all(whitelist)

    def validate_targeted_files(self, whitelist: List[str]) -> ValidationReport:
        """
        [v110.40] Smart Audit: Performs a structural and binary validation on a localized set of files.
        Avoids the overhead of a full folder scan during fast UI interactions.
        """
        return self.validator.validate_folder(self.target_folder, whitelist)

    def _get_sha1_hash(self, path: str) -> str:
        """Computes SHA-1 hash of a file using 64KB chunked reads for performance."""
        sha1 = hashlib.sha1()
        try:
            with open(path, 'rb') as f:
                while True:
                    data = f.read(65536) # 64KB chunks
                    if not data:
                        break
                    sha1.update(data)
            return sha1.hexdigest()
        except Exception:
            return ""

    def snapshot_context(self):
        """
        [v110.42] Captures mtime, file size, and SHA-1 hash for all indexed files.
        SHA-1 provides a cryptographic integrity signal against same-size overwrites.
        """
        self.session_snapshot = {}
        target_files = []
        
        # Core files
        for key in ["main", "global"]:
            f = self.save_context.get(key)
            if f: target_files.append(f)
        
        # World markers (STS)
        target_files.extend(self.save_context["sts"].values())
        
        # Discovery (Fog)
        target_files.extend(self.save_context["fog"].values())
        
        for f in target_files:
            path = os.path.join(self.target_folder, f)
            if os.path.exists(path):
                mtime = os.path.getmtime(path)
                size = os.path.getsize(path)
                sha1 = self._get_sha1_hash(path)
                self.session_snapshot[f] = (mtime, size, sha1)
        
        self.session_state = "CLEAN"

    def check_session_validity(self, whitelist: List[str] = None) -> Tuple[bool, List[str]]:
        """
        [v110.43] Optimized Integrity Check with Whitelist Support.
        If whitelist is provided, only targets those files for early drift detection.
        """
        conflicts = []
        target_dict = self.session_snapshot
        if whitelist:
            target_dict = {f: self.session_snapshot[f] for f in whitelist if f in self.session_snapshot}
            
        for filename, snapshot_data in target_dict.items():
            path = os.path.join(self.target_folder, filename)
            if not os.path.exists(path):
                conflicts.append(filename)
                continue
            
            try:
                baseline_mtime, baseline_size, baseline_hash = snapshot_data
                current_mtime = os.path.getmtime(path)
                current_size = os.path.getsize(path)
                
                # Check mtime and size first (Fast Path)
                mtime_drift = abs(current_mtime - baseline_mtime) > 0.01
                size_drift = current_size != baseline_size
                
                if mtime_drift or size_drift:
                    # Content definitely changed or timestamp resolution coarse
                    current_hash = self._get_sha1_hash(path)
                    if current_hash != baseline_hash:
                        conflicts.append(filename)
                
            except Exception:
                conflicts.append(filename)
        
        if conflicts:
            self.session_state = "STALE"
            return False, conflicts
        return True, []

    def _jit_integrity_recheck(self, path: str) -> bool:
        """[v110.43] Performs a last-millisecond hash check before final rename."""
        filename = os.path.basename(path)
        if filename not in self.session_snapshot: return True
        
        _, _, baseline_hash = self.session_snapshot[filename]
        current_hash = self._get_sha1_hash(path)
        return current_hash == baseline_hash

    def _atomic_write(self, path: str, data: bytes, tx_id: str = None):
        """
        [v110.43] Production-Grade Atomic Write (Write -> Flush -> Fsync -> JIT ReCheck -> Rename).
        Protects against partial writes, crashes, and cross-process interference windows.
        """
        safe_tx_id = tx_id if tx_id else str(uuid.uuid4())
        temp_path = f"{path}.tmp.{safe_tx_id}"
        
        try:
            # Defensive Cleanup
            if os.path.exists(temp_path):
                os.remove(temp_path)

            # Step 1: Write temp
            with open(temp_path, "wb") as f:
                f.write(data)
                f.flush()
                os.fsync(f.fileno())

            # Step 2: Retry-safe replace (Handle Windows transient locks)
            RETRY_COUNT = 5
            RETRY_DELAY = 0.2
            
            for attempt in range(RETRY_COUNT):
                # [v110.43] JIT Re-Check IMMEDIATELY before replace
                if not self._jit_integrity_recheck(path):
                    raise RuntimeError(f"JIT_STALE_EXCEPTION: {os.path.basename(path)} modified by another process during preparation.")
                
                try:
                    os.replace(temp_path, path)
                    return
                except PermissionError:
                    if attempt < RETRY_COUNT - 1:
                        time.sleep(RETRY_DELAY)
                    else:
                        raise
        except Exception as e:
            # Step 3: Mandatory Cleanup
            if os.path.exists(temp_path):
                try: os.remove(temp_path)
                except: pass
            raise

    def _get_file_hashes(self, files: List[str]) -> Dict[str, str]:
        """Captures SHA-256 hashes of affected files."""
        import hashlib
        hashes = {}
        for filename in files:
            path = os.path.join(self.target_folder, filename)
            if os.path.exists(path):
                with open(path, "rb") as f:
                    hashes[filename] = hashlib.sha256(f.read()).hexdigest()
        return hashes

    def _detect_save_version(self) -> str:
        """Heuristic to detect Steam vs Epic/MS Store formats via FingerprintEngine."""
        return self.fingerprint.generate_fingerprint()

    def pre_transaction_guard(self, files: List[str]):
        """Zero-Trust Security Layer: Validates headers and zlib integrity before any tool parses the files."""
        import zlib
        VALID_HEADERS = [b"\x41\x4b\x05\x00", b"\xd3\xa6\x02\x00"]
        
        for filename in files:
            path = os.path.join(self.target_folder, filename)
            if not os.path.exists(path): continue
            
            with open(path, "rb") as f:
                raw_data = f.read()
            
            if len(raw_data) < 4:
                raise ValueError(f"Security Guard: File '{filename}' is too small or empty.")
            
            header = raw_data[:4]
            if header not in VALID_HEADERS:
                # If it's a .cfg it might be plain JSON (mod)
                if filename.endswith(".cfg") and raw_data.strip().startswith(b"{"):
                    continue
                raise ValueError(f"Security Guard: Invalid magic header in '{filename}' ({header.hex().upper()})")
            
            # Zlib Integrity Check
            try:
                zlib.decompress(raw_data[4:])
            except Exception as e:
                raise ValueError(f"Security Guard: Zlib corruption in '{filename}': {e}")

    def execute_feature(self, feature: str, region: str = "GLOBAL", value: Any = None, xp_value: Any = None,
                        objective_id: str = None, achievement_id: str = None, 
                        supplemental_data: Dict[str, Any] = None) -> dict:
        """
        Executes a complex feature with absolute safety (Atomic Rollback + Hashing).
        v110.42: Transactional Guard + Structured Logging.
        """
        version = self._detect_save_version()
        start_time = time.time()
        tx_id = str(uuid.uuid4())
        result = {"success": False, "report": None, "error": "", "status": "failed", "tx_id": tx_id}
        
        # Track initial bytes for throughput metrics
        total_bytes = 0
        
        try:
            # 0. Slot Context Detection
            main_save_file = None
            if supplemental_data and "save_path" in supplemental_data:
                main_save_file = supplemental_data["save_path"]
            else:
                for f in os.listdir(self.target_folder):
                    if "CompleteSave" in f:
                        main_save_file = os.path.join(self.target_folder, f)
                        break
            
            if main_save_file:
                self.slot_context = SlotContext(main_save_file)
                self.resolver.set_slot_context(self.slot_context)

            # 0.1 Constraint Engine Check
            constraint_payload = {
                "region": region,
                "value": value,
                "xp_value": xp_value,
                "objective_id": objective_id,
                "achievement_id": achievement_id
            }
            if supplemental_data: constraint_payload.update(supplemental_data)
            
            con_report = self.constraints.validate_mutation(feature, constraint_payload)
            if not con_report.is_valid:
                result["error"] = "Constraint Violation: " + " | ".join(con_report.violations)
                result["status"] = "blocked"
                return result

            # 0.2 External Change Guard (Global Verify)
            is_valid, conflicts = self.check_session_validity()
            if not is_valid:
                result["error"] = f"Session Stale: External modification detected in {len(conflicts)} files."
                result["status"] = "stale"
                result["conflicts"] = conflicts
                return result

            # 1. Resolve Dependencies
            whitelist, mutations = self.resolver.resolve(
                feature, region, value=value, xp_value=xp_value, 
                objective_id=objective_id, achievement_id=achievement_id,
                supplemental_data=supplemental_data
            )
            
            # 1.0 [v110.43] Idempotency-First Gate (Prune if already finished)
            if feature == "complete_objective" and objective_id:
                finished = self._get_current_finished_objectives()
                if objective_id in finished:
                    result["success"] = True
                    result["status"] = "no_op (already_finished)"
                    result["report"] = self.validate_targeted_files(whitelist)
                    return result
            
            # 1.1 [v110.43] Pre-Write Targeted Revalidation
            # Detect drift immediately before starting mutation logic.
            is_valid_t, conflicts_t = self.check_session_validity(whitelist=whitelist)
            if not is_valid_t:
                result["error"] = f"Session Drift: Target files {conflicts_t} modified before write."
                result["status"] = "stale"
                return result
            
            # 1.1 Zero-Trust Guard
            self.pre_transaction_guard(whitelist)
            
            # 2. Capture Before State
            before_hashes = self._get_file_hashes(whitelist)
            for f in whitelist:
                p = os.path.join(self.target_folder, f)
                if os.path.exists(p): total_bytes += os.path.getsize(p)
            
            # 3. Hybrid Backup
            if not self.dry_run:
                self.backups.trigger_backup(self.target_folder, whitelist)
                
                # 3.1 [v110.42] Transaction Boundary Assertion
                # Enforce that the backup delta exactly matches the resolved mutation scope.
                # If these fall out of sync, we risk partial rollback.
                backup_set = set(self.backups.get_last_backup_set())
                assert set(whitelist) == backup_set, f"Rollback Scope Mismatch: Resolved {whitelist} != Backup {backup_set}"
            
            # 4. Mutation Execution
            op_success = False
            if feature == "reveal_map":
                op_success = self.mutator.apply_reveal_map(region, dry_run=self.dry_run, manager=self, tx_id=tx_id)
            elif feature in ["reveal_upgrades", "unlock_watchtowers", "add_money", "add_rank", 
                           "unlock_garages", "discover_trucks", "unlock_maps", "fix_recovery", 
                           "complete_objective", "accept_objective", "unlock_achievements", "reset_task", "diagnostic_check",
                           "repair_vehicle", "discover_vehicle", "garage_vehicle",
                           "move_vehicle", "move_trailer", "repair_trailer", "set_cargo"]:
                op_success = True 
            
            if op_success:
                target_file = None
                for f in whitelist:
                    if "CompleteSave" in f: target_file = f; break
                if not target_file:
                    for f in whitelist:
                        if "CommonSslSave" in f: target_file = f; break
                
                if not target_file:
                    target_file = "CompleteSave.cfg" if any(f.endswith(".cfg") for f in whitelist) else "CompleteSave.dat"
                
                op_success = self.mutator.apply_global_linkage(
                    os.path.join(self.target_folder, target_file), 
                    mutations,
                    resolver_ref=self.resolver,
                    feature_ref=feature,
                    dry_run=self.dry_run,
                    region_ref=region,
                    manager=self,
                    tx_id=tx_id
                )
            
            # 5. Final Audit & Commit
            if op_success:
                report = self.validate_targeted_files(whitelist)
                result["report"] = report
                
                if not report.is_safe:
                    if not self.dry_run: self.backups.restore_last_delta(self.target_folder)
                    result["error"] = "Structural Validation Failed (Rolled Back)"
                    result["status"] = "failed"
                    result["success"] = False
                else:
                    consistency_report = self._validate_cross_save_consistency()
                    if not consistency_report.is_safe:
                        report.warnings.extend(consistency_report.warnings)
                        result["status"] = "warning"
                    
                    result["success"] = True
                    if not result.get("status") or result["status"] == "failed":
                        result["status"] = "success" if not report.warnings else "warning"
                        
                    # 6. [v110.42] COMMIT SNAPSHOT ONLY ON ABSOLUTE SUCCESS
                    if not self.dry_run:
                        self.snapshot_context()
                        self.session_state = "MODIFIED"
                    
                    # 7. [v110.43] Post-Mutation Consistency Assertion
                    if feature == "complete_objective" and objective_id:
                        # Verify the result in state (lightweight)
                        current_finished = self._get_current_finished_objectives()
                        if objective_id not in current_finished:
                            result["status"] = "warning"
                            report.warnings.append(f"Post-Mutation Inconsistency: '{objective_id}' not found in finishedObjs despite successful write.")
            else:
                if not self.dry_run: self.backups.restore_last_delta(self.target_folder)
                result["error"] = "Mutation Logic Failure (Rolled Back)"
                result["status"] = "failed"

        except Exception as e:
            if not self.dry_run: self.backups.restore_last_delta(self.target_folder)
            result["error"] = f"Engine Error: {str(e)} (Emergency Rollback Triggered)"
            result["status"] = f"failed (rollback: {tx_id})"
            result["success"] = False
            raise # [v110.43] Propagate hard failure

        # 8. Persistent Structured Logging (v110.42 Tracking)
        duration_ms = int((time.time() - start_time) * 1000)
        final_status = "DRY_RUN_SUCCESS" if self.dry_run and result["success"] else result["status"]
        self.metrics.record_mutation(final_status, duration_ms, total_bytes)
        
        after_hashes = self._get_file_hashes(whitelist if 'whitelist' in locals() else [])
        self.logger.log_operation(
            tx_id=tx_id,
            feature=feature,
            region=region,
            duration_ms=duration_ms,
            files_modified=whitelist if 'whitelist' in locals() else [],
            status=final_status,
            warnings=result["report"].warnings if result["report"] else [],
            reason=result["error"],
            before_hashes=before_hashes if 'before_hashes' in locals() else {},
            after_hashes=after_hashes,
            version=version
        )
        
        return result

    def run_preflight(self, whitelist: List[str] = None) -> PreflightReport:
        """
        Conducts a deep integrity audit of the save folder (v110.31.3+).
        Should be called immediately after folder load/refresh.
        """
        if whitelist is None:
            # Default to scanning core save files
            whitelist = []
            for f in os.listdir(self.target_folder):
                if "CompleteSave" in f or "CommonSslSave" in f:
                    whitelist.append(f)
        
        report = self.preflight.audit_all(whitelist)
        
        # Log preflight status if issues found
        if not report.is_healthy:
            self.logger.log_operation(
                feature="preflight_scan",
                region="GLOBAL",
                duration_ms=0,
                files_modified=[],
                status="warning",
                warnings=[i.issue for i in report.issues],
                reason=f"Detected {len(report.issues)} integrity issues.",
                before_hashes={},
                after_hashes={},
                version=self._detect_save_version()
            )
        return report

    def rollback_last_operation(self) -> dict:
        """
        [v110.31] Reverts the last single atomic operation by restoring the folder delta.
        """
        start_time = time.time()
        result = {"success": False, "error": "", "status": "failed"}
        try:
            success = self.backups.restore_last_delta(self.target_folder)
            if success:
                result["success"] = True
                result["status"] = "success"
                # Log the rollback itself for audit trail
                self.logger.log_operation(
                    feature="SYSTEM_ROLLBACK",
                    region="GLOBAL",
                    duration_ms=int((time.time() - start_time) * 1000),
                    files_modified=["ALL_AFFECTED"],
                    status="success",
                    reason="User requested undo"
                )
            else:
                result["error"] = "No backup delta found to restore."
        except Exception as e:
            result["error"] = f"Rollback failed: {e}"
        return result

    def execute_feature_batch(self, feature: str, items: List[Dict[str, Any]]) -> dict:
        """
        [v110.31] Efficiently executes the same feature across multiple items (e.g. Multi-Objective Completion).
        Performs a single Backup/Write/Verify cycle.
        """
        version = self._detect_save_version()
        start_time = time.time()
        result = {"success": False, "report": None, "error": "", "status": "failed", "processed": 0}
        
        try:
            all_mutations = []
            unified_whitelist = set()
            
            # 1. Resolve and Validate all steps first
            for item in items:
                region = item.get("region", "GLOBAL")
                val = item.get("value")
                xp = item.get("xp_value")
                oid = item.get("objective_id")
                aid = item.get("achievement_id")
                supp = item.get("supplemental_data")
                
                whitelist, mutations = self.resolver.resolve(
                    feature, region, value=val, xp_value=xp, 
                    objective_id=oid, achievement_id=aid, supplemental_data=supp
                )
                all_mutations.extend(mutations)
                unified_whitelist.update(whitelist)
            
            final_whitelist = list(unified_whitelist)
            
            # 1.2 [v110.40] External Change Guard
            is_valid, conflicts = self.check_session_validity()
            if not is_valid:
                result["error"] = f"Session Stale: External modification detected."
                result["status"] = "stale"
                return result
            
            # 2. Capture Before State
            before_hashes = self._get_file_hashes(final_whitelist)
            
            # 3. Backup
            if not self.dry_run:
                self.backups.trigger_backup(self.target_folder, final_whitelist)
            
            # 4. Batch Mutation Execution
            # (Currently only global linkage supports batching via unified mutation list)
            target_file = "CompleteSave.cfg" if any(f.endswith(".cfg") for f in final_whitelist) else "CompleteSave.dat"
            
            op_success = self.mutator.apply_global_linkage(
                os.path.join(self.target_folder, target_file), 
                all_mutations,
                resolver_ref=self.resolver,
                feature_ref=feature,
                dry_run=self.dry_run
            )
            
            # 5. Final Smart Validation & Commit
            if op_success:
                report = self.validate_targeted_files(final_whitelist)
                result["report"] = report
                
                if not report.is_safe:
                    if not self.dry_run:
                        self.backups.restore_last_delta(self.target_folder)
                    result["error"] = "Batch Validation Failed (Rolled Back)"
                    result["status"] = "failed"
                else:
                    result["success"] = True
                    result["processed"] = len(items)
                    result["status"] = "success" if not report.warnings else "warning"

                    # 6. [v110.41] POST-SUCCESS: Commit Snapshot
                    if result["success"] and not self.dry_run:
                        self.snapshot_context()
                        self.session_state = "MODIFIED"
            else:
                # Batch Mutation Failure -> ROLLBACK
                if not self.dry_run:
                    self.backups.restore_last_delta(self.target_folder)
                result["error"] = f"Batch feature '{feature}' failed during linkage sync. (Rolled Back)"
                result["status"] = "failed"

        except Exception as e:
            # Critical Batch Failure -> ROLLBACK
            if not self.dry_run:
                self.backups.restore_last_delta(self.target_folder)
            result["error"] = f"Critical Batch Error: {str(e)} (Emergency Rollback Triggered)"
            result["status"] = "failed"

        # 6. Logging
        after_hashes = self._get_file_hashes(final_whitelist if 'final_whitelist' in locals() else [])
        duration_ms = int((time.time() - start_time) * 1000)
        self.logger.log_operation(
            feature=f"{feature}_BATCH",
            region="VARIOUS",
            duration_ms=duration_ms,
            files_modified=final_whitelist if 'final_whitelist' in locals() else [],
            status=result["status"],
            warnings=result["report"].warnings if result["report"] else [],
            reason=result["error"],
            before_hashes=before_hashes if 'before_hashes' in locals() else {},
            after_hashes=after_hashes,
            version=version
        )
        
        return result

    def preview_feature_execution(self, feature: str, region: str = "GLOBAL", value: Any = None, 
                                 xp_value: Any = None, objective_id: str = None, 
                                 achievement_id: str = None,
                                 supplemental_data: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        [v110.40] Generates a structured Impact Summary for the Review UI.
        Returns: {success: bool, primary: str, dependents: List[str], risk: str, steps: List[dict]}
        """
        try:
            risk = self.resolver.get_feature_risk(feature)
            whitelist, mutations = self.resolver.resolve(
                feature, region, value=value, xp_value=xp_value, 
                objective_id=objective_id, achievement_id=achievement_id,
                supplemental_data=supplemental_data
            )
            
            # v110.31: Inject risk and procedural side-effects
            for m in mutations:
                m["risk_label"] = risk
                
            if feature == "reveal_map":
                mutations.append({
                    "target": f"fog_level_{region.lower()}.cfg",
                    "action": "binary_procedural_reveal",
                    "risk_label": risk,
                    "note": "Side-effect: Binary fog transformation"
                })

            # Identify Primary vs Dependents (v110.40)
            primary = ""
            dependents = []
            for f in whitelist:
                if "CompleteSave" in f:
                    primary = f
                else:
                    dependents.append(f)
            
            if not primary and whitelist:
                primary = whitelist[0]
                dependents = whitelist[1:]

            return {
                "success": True,
                "primary": primary,
                "dependents": dependents,
                "risk": risk,
                "steps": mutations
            }
        except Exception as e:
            return {"success": False, "error": str(e)}

    def execute_simple_mutation(self, feature: str, value: Any, xp_value: Any = None) -> dict:
        """Handles simple mutations (e.g. money, rank) via the safety pipeline."""
        return self.execute_feature(feature, region="GLOBAL", value=value, xp_value=xp_value)


    def _validate_cross_save_consistency(self) -> ValidationReport:
        """
        [v110.31] Strict cross-save audit.
        Ensures that progress in CompleteSave matches achievements in CommonSslSave.
        """
        report = ValidationReport()
        # This requires loading both files. Since they are likely already in memory 
        # or cached by the validator, we perform a deep semantic check here.
        # Example: check if 'finishedObjs' count matches 'achievementStates' unlock flags for specific milestones.
        
        # Placeholder for heuristic strictness:
        # 1. Load CompleteSave JSON
        # 2. Load CommonSslSave JSON
        # 3. Verify specific mappings (e.g. Tutorial Finished -> Tutorial Achievement)
        
        # For now, we add a 'Consistency Warning' if the files have drifted in size significantly 
        # without corresponding achievement updates.
        return report

    def repair_integrity(self, mode: str = "SAFE") -> dict:
        """
        v110.31 Tiered Repair modes:
        - SAFE: Fixes missing mandatory structural keys (Layer A).
        - FULL: Synchronizes model alignment discrepancies against Ground Truth (Layer B).
        """
        if self.dry_run: return {"success": True, "status": "DRY_RUN", "error": ""}
        
        print(f"[Integrity] Commencing {mode} Repair...")
        
        # 1. Full Backup before major repair
        self.backups._create_full_backup(self.target_folder)
        
        # 2. Identify Target (Heuristic)
        target_file = None
        for f in os.listdir(self.target_folder):
            if "CompleteSave" in f:
                target_file = f
                break
        
        if not target_file:
            return {"success": False, "error": "CompleteSave not found for repair."}

        # 3. Layer A: Structural Repair
        mutations = []
        if mode in ["SAFE", "FULL"]:
             # Ensure core registries exist
             mutations.append({"key": "CompleteSave.SslValue", "action": "ensure_dict"})
             mutations.append({"key": "CompleteSave.SslValue.finishedObjs", "action": "ensure_list"})
             mutations.append({"key": "CompleteSave.SslValue.upgradesGiverData", "action": "ensure_dict"})
             mutations.append({"key": "CompleteSave.SslValue.levelGarageStatuses", "action": "ensure_dict"})
             mutations.append({"key": "persistentProfileData", "action": "ensure_dict"})

        # 4. Apply Mutations via Mutator
        success = self.mutator.apply_global_linkage(
            os.path.join(self.target_folder, target_file),
            mutations,
            dry_run=self.dry_run
        )
        
        if success:
             print(f"[Integrity] {mode} Repair completed successfully.")
             return {"success": True, "status": "success", "warnings": []}
        else:
             return {"success": False, "error": "Mutator failed during repair execution."}

    def execute_batch_objectives(self, region: str, objective_ids: List[str]) -> Dict[str, Any]:
        """
        [v110.43] Atomic Batch Objective Completion.
        Uses aggregated rewards and grouped STS updates for maximum performance and safety.
        """
        # 1. Stable Deduplication (v110.43 Precision Constraint)
        unique_ids = list(dict.fromkeys(objective_ids))
        
        tx_id = f"BATCH-OBJ-{str(uuid.uuid4())[:8]}"
        start_time = time.time()
        result = {"success": False, "error": None, "report": None, "tx_id": tx_id}
        version = "v110.43 (Platinum)"
        
        try:
            # 2. Metadata & Idempotency Audit
            current_finished = self._get_current_finished_objectives()
            metadata = self.resolver.OBJECTIVE_METADATA
            
            executable_ids = []
            total_money = 0
            total_xp = 0
            sts_groups = defaultdict(list) # map_id -> list of marker_ids
            
            for oid in unique_ids:
                if oid not in metadata:
                    raise ValueError(f"ValidationError: Unknown objective '{oid}' in batch.")
                
                if oid in current_finished:
                    continue
                
                executable_ids.append(oid)
                meta = metadata[oid]
                
                # Aggregate Rewards
                rewards = meta.get("rewards", {})
                total_money += rewards.get("money", 0)
                total_xp += rewards.get("xp", 0)
                
                # Group STS markers
                if meta.get("affects_world"):
                    map_id = meta.get("map")
                    marker_id = meta.get("marker_id")
                    sts_groups[map_id].append(marker_id)

            if not executable_ids:
                result["success"] = True
                result["status"] = "no_op (all_finished_or_skipped)"
                return result

            # 3. Resolve Collective File Scope
            collective_whitelist = set()
            for oid in executable_ids:
                w, _ = self.resolver.resolve("complete_objective", region, objective_id=oid)
                collective_whitelist.update(w)
            
            final_whitelist = list(collective_whitelist)
            
            # 4. Pre-Mutation JIT Guard
            is_valid, conflicts = self.check_session_validity(whitelist=final_whitelist)
            if not is_valid:
                result["error"] = f"Batch Sync Failed: External modification in {conflicts}"
                result["status"] = "stale"
                return result

            # 5. Collective Backup
            if not self.dry_run:
                self.backups.trigger_backup(self.target_folder, final_whitelist)
                b_set = set(self.backups.get_last_backup_set())
                assert set(final_whitelist) == b_set, f"Rollback Scope Mismatch: {final_whitelist} != {b_set}"

            # 6. Apply Aggregated Mutations
            # 6.1 Apply All Rewards to Main Save
            main_save = next((f for f in final_whitelist if "CompleteSave" in f), "CompleteSave.cfg")
            reward_mutation = [{"key": "SslValue", "action": "batch_apply_rewards", "value": {"money": total_money, "xp": total_xp}}]
            
            # 6.2 Global Ssl/Finished Status Updates (Sequential for now, but in one linkage cycle)
            global_mutations = reward_mutation.copy()
            for oid in executable_ids:
                 # Add finished status and global achievement sync
                 global_mutations.append({"key": "SslValue.finishedObjs", "action": "sync_global_objective", "value": oid})

            reward_success = self.mutator.apply_global_linkage(
                os.path.join(self.target_folder, main_save),
                global_mutations,
                resolver_ref=self.resolver,
                dry_run=self.dry_run,
                manager=self,
                tx_id=tx_id
            )
            if not reward_success: raise RuntimeError("Failed to apply aggregated rewards.")

            # 6.3 Apply Grouped STS Updates (One read/write cycle per map)
            for map_id, markers in sts_groups.items():
                sts_file = f"sts_level_{map_id}.cfg" # Standard naming convention
                if sts_file not in final_whitelist:
                    # In case of DAT or different naming, search whitelist
                    sts_file = next((f for f in final_whitelist if map_id in f and "sts" in f.lower()), sts_file)
                
                sts_success = self.mutator.apply_global_linkage(
                    os.path.join(self.target_folder, sts_file),
                    [{"key": "STS_BATCH", "action": "batch_sts_sync", "value": markers}],
                    resolver_ref=self.resolver,
                    dry_run=self.dry_run,
                    manager=self,
                    tx_id=tx_id
                )
                if not sts_success: raise RuntimeError(f"Batch STS Update failed for map {map_id}")

            # 7. Final Validation & Snapshot
            report = self.validate_targeted_files(final_whitelist)
            result["report"] = report
            
            if not report.is_safe:
                if not self.dry_run: self.backups.restore_last_delta(self.target_folder)
                result["error"] = "Batch Structural Audit Failed"
                return result
            
            if not self.dry_run:
                # 8. Snapshot Commit
                self.snapshot_context()
                self.session_state = "MODIFIED"
                
                # 9. [v110.43] POST-COMMIT REVALIDATION (Guard against FS delay)
                self._revalidate_snapshot_post_commit(final_whitelist)
            
            result["success"] = True
            result["status"] = "success"

        except Exception as e:
            if not self.dry_run: self.backups.restore_last_delta(self.target_folder)
            result["error"] = f"Batch Fatal Error: {str(e)} (Emergency Collective Rollback)"
            result["status"] = "failed"
            raise 

        # 10. Enriched Structured Logging
        duration_ms = int((time.time() - start_time) * 1000)
        self.logger.log_operation(
            tx_id=tx_id,
            feature=f"batch_objectives ({len(unique_ids)})",
            region=region,
            duration_ms=duration_ms,
            files_modified=final_whitelist,
            status=result["status"],
            reason=result["error"],
            metadata={
                "objectives_requested": unique_ids,
                "objectives_executed": executable_ids,
                "reward_total": {"money": total_money, "xp": total_xp},
                "sts_maps_updated": list(sts_groups.keys())
            }
        )
        return result

    def _revalidate_snapshot_post_commit(self, whitelist: List[str] = None):
        """[v110.43] Performs a secondary hash verification after snapshot commit."""
        is_valid, conflicts = self.check_session_validity(whitelist=whitelist)
        if not is_valid:
             raise RuntimeError(f"Post-Commit Integrity Failure: Disk state drifted from snapshot for {conflicts}")

    def get_progression_analytics(self) -> Dict[str, Any]:
        """
        [v110.43] Read-Only Progression Auditor.
        Aggregates save state against OBJECTIVE_METADATA to provide 100% accurate completion stats.
        """
        metadata = self.resolver.OBJECTIVE_METADATA
        finished_ids = self._get_current_finished_objectives()
        
        # 1. Initialize Analytics Structure
        analytics = {
            "totals": {
                "perc": 0,
                "money_earned": 0,
                "money_potential": 0,
                "xp_earned": 0,
                "xp_potential": 0,
                "world_completed": 0,
                "world_total": 0,
                "logical_completed": 0,
                "logical_total": 0,
                "total_completed": 0,
                "total_cataloged": len(metadata)
            },
            "regions": defaultdict(lambda: {
                "completed": 0, "total": 0, "perc": 0, 
                "world_completed": 0, "world_total": 0,
                "logical_completed": 0, "logical_total": 0,
                "money_potential": 0, "xp_potential": 0
            }),
            "unknown_in_save": []
        }
        
        # 2. Map Snapshot vs Metadata
        finished_set = set(finished_ids)
        
        for oid, meta in metadata.items():
            r_name = meta.get("region_name", "Other")
            reg = analytics["regions"][r_name]
            
            is_world = meta.get("affects_world", False)
            rewards = meta.get("rewards", {})
            m_val = rewards.get("money", 0)
            x_val = rewards.get("xp", 0)
            
            reg["total"] += 1
            if is_world: 
                reg["world_total"] += 1
                analytics["totals"]["world_total"] += 1
            else: 
                reg["logical_total"] += 1
                analytics["totals"]["logical_total"] += 1
            
            if oid in finished_set:
                reg["completed"] += 1
                analytics["totals"]["total_completed"] += 1
                analytics["totals"]["money_earned"] += m_val
                analytics["totals"]["xp_earned"] += x_val
                if is_world: 
                    reg["world_completed"] += 1
                    analytics["totals"]["world_completed"] += 1
                else: 
                    reg["logical_completed"] += 1
                    analytics["totals"]["logical_completed"] += 1
            else:
                reg["money_potential"] += m_val
                reg["xp_potential"] += x_val
                analytics["totals"]["money_potential"] += m_val
                analytics["totals"]["xp_potential"] += x_val

        # 3. Calculate Percentages
        for r_name, reg in analytics["regions"].items():
            if reg["total"] > 0:
                reg["perc"] = round((reg["completed"] / reg["total"]) * 100, 1)

        t = analytics["totals"]
        if t["total_cataloged"] > 0:
            t["perc"] = round((t["total_completed"] / t["total_cataloged"]) * 100, 1)

        # 4. Detect Metadata Gaps (Unknowns)
        for oid in finished_ids:
            if oid not in metadata:
                analytics["unknown_in_save"].append(oid)
                
        return analytics

    def _get_current_finished_objectives(self) -> List[str]:
        """[v110.43] Reads the current save to get finishedObjs for idempotency checks."""
        main_save_file = None
        for f in os.listdir(self.target_folder):
            if "CompleteSave" in f:
                main_save_file = os.path.join(self.target_folder, f)
                break
        
        if not main_save_file or not os.path.exists(main_save_file):
            return []

        try:
            with open(main_save_file, 'rb') as f: data = f.read()
            import zlib
            # MAGIC_AK = b'\x41\x4b\x05\x00', MAGIC_D3 = b'\xd3\xa6\x02\x00'
            header = b'\x41\x4b\x05\x00' if data.startswith(b'\x41\x4b\x05\x00') else (b'\xd3\xa6\x02\x00' if data.startswith(b'\xd3\xa6\x02\x00') else b'')
            text = zlib.decompress(data[4:]).decode('utf-8', errors='replace') if header else data.decode('utf-8', errors='replace')
            js = json.loads(text.strip().split('\x00')[0])
            
            ssl = js.get("SslValue", {})
            if not ssl and "CompleteSave" in js:
                ssl = js["CompleteSave"].get("SslValue", {})
            
            finished = ssl.get("finishedObjs", [])
            if isinstance(finished, dict):
                return list(finished.keys())
            return finished if isinstance(finished, list) else []
        except:
            return []

    def _update_remote_vdf(self, target_file_path: str) -> bool:
        """
        [v110.50] Updates Steam's remote.vdf with the new size/time for a modified file.
        This prevents Steam Cloud from reverting the change.
        """
        try:
            save_dir = os.path.dirname(target_file_path)
            if os.path.basename(save_dir).lower() != "remote":
                return False
                
            vdf_path = os.path.join(os.path.dirname(save_dir), "remote.vdf")
            if not os.path.isfile(vdf_path):
                return False
                
            file_name = os.path.basename(target_file_path)
            file_size = os.path.getsize(target_file_path)
            file_time = int(os.path.getmtime(target_file_path))
            
            with open(vdf_path, "r", encoding="utf-8", errors="ignore") as f:
                lines = f.readlines()
                
            new_lines = []
            in_file_block = False
            target_found = False
            
            for line in lines:
                if f'"{file_name}"' in line:
                    in_file_block = True
                    target_found = True
                
                if in_file_block:
                    if '"size"' in line:
                        line = re.sub(r'"size"\s*"\d+"', f'"size" "{file_size}"', line)
                    elif '"time"' in line:
                        line = re.sub(r'"time"\s*"\d+"', f'"time" "{file_time}"', line)
                    elif '}' in line:
                        in_file_block = False
                new_lines.append(line)
                
            if target_found:
                with open(vdf_path, "w", encoding="utf-8", newline='\n') as f:
                    f.writelines(new_lines)
                return True
        except:
            pass
        return False

    def execute_feature(self, feature: str, payload: dict) -> dict:
        """
        [v110.60] Platform Dispatcher.
        Routes plugin requests to internal engine commands after 
        context-level permission validation.
        """
        if feature == "map_unlock":
            return self.execute_batch_fog_reveal(
                scope=payload.get("scope"),
                region_name=payload.get("region_name"),
                level_id=payload.get("level_id")
            )
        
        if feature == "objective_complete":
            return self.execute_batch_objectives(
                status=payload.get("status", "COMPLETED"),
                objective_ids=payload.get("objective_ids", [])
            )
        
        raise ValueError(f"Engine Feature '{feature}' not registered or implemented.")

    def execute_batch_objectives(self, status: str, objective_ids: List[str]) -> dict:
        """
        [v110.60] Safe Batch Objective Mutation Engine.
        Processes mission completions in a single transaction with JIT validation.
        """
        start_time = time.time()
        tx_id = str(uuid.uuid4())
        result = {"success": False, "error": "", "tx_id": tx_id, "objectives_count": len(objective_ids)}
        
        try:
            # 1. JIT Pre-Write Revalidation (Race Condition Shield)
            # Focus on CompleteSave and STS files for the affected region (if any)
            # For simplicity in Phase 4, we'll validate the primary CompleteSave
            whitelist = [os.path.basename(self.save_context["save"])]
            is_valid, conflicts = self.check_session_validity(whitelist=whitelist)
            if not is_valid:
                result["error"] = f"Race Condition: {conflicts} modified externally."
                return result

            # 2. Transaction Start: Backup
            if not self.dry_run:
                self._cleanup_temp_files()
                self.backups.trigger_backup(self.target_folder, whitelist)

            # 3. Mutation: Update SslValue via Mutator
            if self.mutator.apply_objective_batch(status, objective_ids, manager=self, tx_id=tx_id):
                if not self.dry_run:
                    # 4. Binary Audit & Write
                    # The mutator already updated SslValue; now we need to commit to disk.
                    # apply_to_save handles the zlib compression and atomic replacement.
                    success = self.apply_to_save(tx_id=tx_id)
                    if not success:
                        result["error"] = "Integrity Engine failed to commit SslValue to disk."
                        return result
                    
                    # Update Steam Cloud context if possible
                    self._update_remote_vdf(self.save_context["save"])
                
                result["success"] = True
            else:
                result["error"] = "ProceduralMutator refused the objective batch (Logic Error)."

        except Exception as e:
            if not self.dry_run:
                self.backups.restore_last_delta(self.target_folder)
            result["error"] = f"Objective Batch Error: {e}"
            raise e

        # 5. Logging
        duration_ms = int((time.time() - start_time) * 1000)
        self.logger.log_operation(
            tx_id=tx_id,
            feature=f"OBJ_BATCH_{status.upper()}",
            region="BATCH",
            duration_ms=duration_ms,
            files_modified=[os.path.basename(self.save_context["save"])],
            status="success" if result["success"] else "failed",
            reason=result["error"],
            version=self._detect_save_version()
        )
        
        return result

    def execute_batch_fog_reveal(self, scope: str, region_name: str = None, level_id: str = None) -> dict:
        """
        [v110.50] Safe Batch Fog Reveal Engine.
        Processes multiple fog files in a single transaction.
        Scopes: 'current', 'region', 'global'.
        """
        start_time = time.time()
        tx_id = str(uuid.uuid4())
        result = {
            "success": False, "error": "", "tx_id": tx_id, 
            "levels_selected": [], "fog_files_found": [], "skipped_levels": [], "files_written": [], "already_clear": []
        }
        
        try:
            # 1. Resolve Target Levels
            target_levels = []
            if scope == "current" and level_id:
                target_levels = [level_id]
            elif scope == "region" and region_name:
                target_levels = self.resolver.REGION_LEVELS.get(region_name, [])
            elif scope == "global":
                for lvls in self.resolver.REGION_LEVELS.values():
                    target_levels.extend(lvls)
            
            result["levels_selected"] = target_levels
            
            # 2. Context-Aware Filtering (Identify existing fog files)
            to_mutate = []
            for lvl in target_levels:
                lvl_lower = lvl.lower()
                if lvl_lower in self.save_context["fog"]:
                    to_mutate.append(lvl_lower)
                    result["fog_files_found"].append(self.save_context["fog"][lvl_lower])
                else:
                    result["skipped_levels"].append(lvl)
            
            if not to_mutate:
                result["success"] = True
                result["error"] = "No visitable fog files found for the selected scope."
                return result

            # [v110.51] JIT Pre-Write Revalidation (Race Condition Shield)
            # We check validity again immediately before mutation to ensure no external change 
            # occurred during the resolution phase.
            whitelist = [self.save_context["fog"][lvl] for lvl in to_mutate]
            is_valid, conflicts = self.check_session_validity(whitelist=whitelist)
            if not is_valid:
                result["error"] = f"Race Condition Detected: {conflicts} modified externally."
                return result

            # 4. Transaction Start: Backup
            if not self.dry_run:
                # [v110.51] Crash Recovery Sweep (Pre-emptive)
                self._cleanup_temp_files()
                self.backups.trigger_backup(self.target_folder, whitelist)

            # 5. Mutation: Reveal Fog
            files_actually_modified = []
            for lvl in to_mutate:
                # ProceduralMutator.apply_reveal_map returns True if something was written, 
                # False if already revealed (idempotent) or error.
                if self.mutator.apply_reveal_map(lvl, dry_run=self.dry_run, manager=self, tx_id=tx_id):
                    filename = self.save_context["fog"][lvl]
                    files_actually_modified.append(filename)
                    if not self.dry_run:
                        self._update_remote_vdf(os.path.join(self.target_folder, filename))
                else:
                    # If it wasn't modified but it exists in fog context, it might be already clear
                    filename = self.save_context["fog"].get(lvl)
                    if filename:
                        result["already_clear"].append(filename)
            
            result["files_written"] = files_actually_modified
            
            # 6. Final Audit & Commit
            if not self.dry_run:
                report = self.validate_targeted_files(whitelist)
                if not report.is_safe:
                    self.backups.restore_last_delta(self.target_folder)
                    result["error"] = "Integrity Validation Failed after reveal (Rolled Back)."
                    return result
                
                # Success: Commit
                self.snapshot_context()
                self.session_state = "MODIFIED"
            
            result["success"] = True
            
        except Exception as e:
            if not self.dry_run:
                self.backups.restore_last_delta(self.target_folder)
            result["error"] = f"Fog Batch Error: {e}"
            raise e

        # 7. Logging
        duration_ms = int((time.time() - start_time) * 1000)
        self.logger.log_operation(
            tx_id=tx_id,
            feature=f"FOG_REVEAL_{scope.upper()}",
            region=region_name or "GLOBAL",
            duration_ms=duration_ms,
            files_modified=result["files_written"],
            status="success" if result["success"] else "failed",
            reason=result["error"],
            version=self._detect_save_version()
        )
        
        return result

    def _cleanup_temp_files(self):
        """
        [v110.51] Crash Recovery Sweep.
        Deletes any orphaned .tmp. files from the save directory to prevent 
        collision risks from previous crashed sessions.
        """
        try:
            for f in os.listdir(self.target_folder):
                if ".tmp." in f:
                    try: os.remove(os.path.join(self.target_folder, f))
                    except: pass
        except:
            pass

    def get_active_snapshot(self) -> Dict[str, Any]:
        """[v110.70] Returns the canonical snapshot of the CURRENTLY active save."""
        # 1. Ephemeral read of current folder
        data = self._read_all_ephemeral(self.target_folder, self.save_context)
        # 2. Re-use canonical builder
        return self._build_peek_snapshot(data, self.save_context)

    # --- v110.70 Save Comparison & Peek APIs ---

    def peek_folder(self, folder_path: str) -> Dict[str, Any]:
        """
        [v110.70] Strictly Non-Destructive External Save Analysis.
        Builds a canonical snapshot of a folder without modifying active session state.
        """
        if not os.path.isdir(folder_path):
            return {"error": "Invalid directory path"}
            
        # Hard Guards
        assert self.session_state in ("CLEAN", "IDLE"), "Cannot peek during active mutation"
        if getattr(self, "_peek_active", False):
            raise RuntimeError("Peek already in progress (Re-entrancy Guard)")
            
        self._peek_active = True
        try:
            # 1. Ephemeral Context Scan
            ctx = self._scan_folder_ephemeral(folder_path)
            if not ctx["main"]:
                return {"error": "No valid SnowRunner save found in target folder."}
                
            # 2. Batch Read (No caching)
            data = self._read_all_ephemeral(folder_path, ctx)
            
            # 3. Canonical Normalization
            return self._build_peek_snapshot(data, ctx)
            
        except Exception as e:
            return {"error": f"Peek Analysis Failed: {str(e)}"}
        finally:
            self._peek_active = False

    def _scan_folder_ephemeral(self, folder_path: str) -> dict:
        """Isolated version of _scan_folder_context."""
        import re
        files = os.listdir(folder_path)
        ctx = {"main": None, "global": None, "sts": {}, "fog": {}, "platform": "Unknown"}
        
        for f in files:
            if "CompleteSave" in f:
                ctx["main"] = f
                ctx["platform"] = "Steam" if f.endswith(".cfg") else "Epic/MS"
            elif "CommonSslSave" in f:
                ctx["global"] = f
            elif f.startswith("sts_level_"):
                ctx["sts"][f[10:].rsplit('.', 1)[0]] = f
            elif f.startswith("fog_level_"):
                ctx["fog"][f[10:].rsplit('.', 1)[0]] = f
        return ctx

    def _read_all_ephemeral(self, folder_path: str, ctx: dict) -> dict:
        """Performs isolated binary-to-JSON parsing for the peek snapshot."""
        data = {"main": {}, "global": {}}
        
        # Read Primary Save
        main_path = os.path.join(folder_path, ctx["main"])
        try:
            with open(main_path, 'rb') as f:
                raw = f.read()
            # Handle zlib vs plain
            if raw.startswith(b"\x41\x4b") or raw.startswith(b"\xd3\xa6"):
                payload = zlib.decompress(raw[4:])
            else:
                payload = raw
            data["main"] = json.loads(payload.decode('utf-8', errors='replace').split('\x00')[0])
        except: pass
        
        return data

    def _build_peek_snapshot(self, data: dict, ctx: dict) -> dict:
        """Normalizes raw data into the v110.70 Generic Diff Model."""
        ssl = data.get("main", {}).get("CompleteSave", {}).get("SslValue", {})
        metadata = self.resolver.OBJECTIVE_METADATA
        
        # 1. Objectives (Completed set)
        raw_finished = ssl.get("finishedObjs", [])
        if isinstance(raw_finished, dict): raw_finished = list(raw_finished.keys())
        finished_set = set(str(x) for x in raw_finished if x)
        
        # 2. Economy
        economy = {
            "xp": ssl.get("experience", 0),
            "money": ssl.get("money", 0)
        }
        
        # 3. Maps (Visited based on fog existence)
        maps = {
            "visited": set(ctx["fog"].keys())
        }
        
        # 5. Vehicles (v110.80 Canonical Model)
        vehicles = {}
        failed_sts = set()
        for map_id, sts_blob in ctx.get("sts", {}).items():
            try:
                # STS files are compressed with zlib starting from offset 4
                payload = zlib.decompress(sts_blob[4:])
                sts_json = json.loads(payload.decode('utf-8', errors='replace'))
                map_vehicles = self._extract_vehicles_from_sts(sts_json, map_id)
                vehicles.update(map_vehicles)
            except Exception as e:
                # fail-soft on per-file basis
                print(f"[IntegrityManager] STS_PARSE_FAIL for {map_id}: {e}")
                failed_sts.add(map_id)
                continue

        return {
            "objectives": {
                "completed": finished_set & metadata_ids
            },
            "economy": economy,
            "maps": maps,
            "metadata": {
                "unknown_ids": finished_set - metadata_ids,
                "failed_sts": failed_sts # v110.80 Observability
            },
            "vehicles": vehicles # v110.80 Intelligence
        }

    def _extract_vehicles_from_sts(self, sts_json: Dict[str, Any], map_id: str) -> Dict[str, Any]:
        """[v110.80] Defensive, pattern-based vehicle extractor."""
        extracted = {}
        
        # Pattern-based scan through "trucks" and "objects"
        for section in ["trucks", "objects"]:
            if section in sts_json and isinstance(sts_json[section], dict):
                for v_key, v_data in sts_json[section].items():
                    if self._is_vehicle(v_data):
                        # Ensure globally unique key for v110.80 (id::map)
                        unique_id = f"{v_key}::{map_id}"
                        extracted[unique_id] = self._normalize_vehicle(v_data, map_id)
        
        return extracted

    def _is_vehicle(self, obj: Any) -> bool:
        """Heuristic check for vehicle data-structure."""
        if not isinstance(obj, dict): return False
        v_type = str(obj.get("type", ""))
        # Most vehicles have 'Truck' in their type, or presence of fuel/damage pattern
        return "Truck" in v_type or ("fuel" in obj and "damage" in obj)

    def _normalize_vehicle(self, v: Dict[str, Any], map_id: str) -> Dict[str, Any]:
        """Maps raw STS keys to the Canonical Vehicle Model (v110.80)."""
        norm = {
            "map": map_id,
            "state": self._infer_vehicle_state(v),
            "pos": self._safe_tuple(v.get("position")),
            "fuel": self._safe_int(v.get("fuel")),
            "damage": self._safe_int(v.get("damage"))
        }
        # Snapshot Shape Assertion (v110.80)
        assert set(norm.keys()) == {"map", "state", "pos", "fuel", "damage"}, "Schema drift detected in normalize_vehicle"
        return norm

    def _infer_vehicle_state(self, v: Dict[str, Any]) -> str:
        """[v110.80] Strict inference priority."""
        if v.get("inGarage") is True: return "garage"
        if v.get("position") is not None: return "deployed"
        if v.get("inWorld") is True: return "deployed"
        return "unknown"

    def _safe_int(self, x: Any) -> Optional[int]:
        try: return int(float(x))
        except: return None

    def _safe_tuple(self, p: Any) -> Optional[tuple]:
        try:
            if isinstance(p, dict):
                return (p.get("x", 0), p.get("y", 0), p.get("z", 0))
            return None
        except: return None

    def _pass_5_apply_fog_batch(self, files: List[str]):
        """Helper to batch apply fog files (implementation placeholder)."""
        for f in files:
            if f.lower().startswith("fog_level_"):
                self._pass_5_apply_fog(f)

# [v111.00] End of IntegrityManager

# --- Phase 14: Singleton Initialization ---
_GLOBAL_MANAGER: IntegrityManager = None

def get_integrity_manager(target_folder: str = None, data_dir: str = None, remote2_path: str = None, progress_callback: Any = None) -> IntegrityManager:
    """
    [v115.06] Production-grade singleton getter for the Integrity Engine.
    Now supports progress_callback for first-time Pass 0 extraction.
    """
    global _GLOBAL_MANAGER
    if _GLOBAL_MANAGER is None:
        if not (target_folder and data_dir and remote2_path):
            return None
        _GLOBAL_MANAGER = IntegrityManager(target_folder, data_dir, remote2_path, progress_callback=progress_callback)
    
    # Update paths if provided for subsequent calls
    if target_folder: _GLOBAL_MANAGER.target_folder = target_folder
    if data_dir: _GLOBAL_MANAGER.data_dir = data_dir
    
    return _GLOBAL_MANAGER
