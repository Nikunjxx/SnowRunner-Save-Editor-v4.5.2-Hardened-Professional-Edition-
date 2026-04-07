import logging
import threading
import os
import time
from typing import Dict, Any, Optional, Tuple, List, Set
from exceptions import SnowRunnerEngineError
from slot_resolver import SlotContext, SlotResolver
from hydration import SaveLoader, FrozenContext
from schema import SchemaContract
from debug import HashEngine
from report import HydrationReport, Severity, Verdict
from mapping import DERIVED_MAP

logger = logging.getLogger("EnginePipeline")

class EnginePipeline:
    """
    The Deterministic Supreme Singleton.
    Refined for Root-Key Agnosticism and High-Performance Audit.
    """
    _LOCK_REGISTRY = {}
    _REGISTRY_LOCK = threading.Lock()

    def __init__(self, slot_ctx: SlotContext):
        self.slot = slot_ctx
        self.report = HydrationReport(slot_ctx.slot_index)
        self.raw_data: Dict[str, Any] = {}
        self.frozen_ctx: Optional[FrozenContext] = None

    @classmethod
    def get_slot_lock(cls, slot_idx: int) -> threading.Lock:
        with cls._REGISTRY_LOCK:
            if slot_idx not in cls._LOCK_REGISTRY:
                cls._LOCK_REGISTRY[slot_idx] = threading.Lock()
            return cls._LOCK_REGISTRY[slot_idx]

    def _build_derived_state(self):
        """Projects raw save data into the standardized 'derived' namespace."""
        derived = {}
        
        for internal_path, raw_path in DERIVED_MAP.items():
            # Traverse raw_path (e.g. CompleteSave.SslValue...)
            parts = raw_path.split(".")
            val = self.raw_data
            for p in parts:
                if isinstance(val, dict):
                    val = val.get(p)
                else:
                    val = None
                    break
            
            # Place in derived (e.g. player.money)
            # Fix: Ensure we correctly handle missing paths during projection
            if val is None:
                logger.warning(f"DERIVED_MISSING: Path {raw_path} not found in state.")
            
            d_parts = internal_path.split(".")
            d_cursor = derived
            for dp in d_parts[:-1]:
                if dp not in d_cursor:
                    d_cursor[dp] = {}
                d_cursor = d_cursor[dp]
            d_cursor[d_parts[-1]] = val
            
        self.raw_data["derived"] = derived

    def run_hydration(self):
        """
        [PH1-PIP-002] Multi-Stage Supremacy Pipeline.
        Safe for all Slot-Key permutations.
        """
        start_time = time.perf_counter()
        slot_lock = self.get_slot_lock(self.slot.slot_index)
        
        if not slot_lock.acquire(blocking=True, timeout=5):
             logger.error(f"LOCK_ABORT: Slot {self.slot.slot_index} locked.")
             self.report.add_entry("LOCK_ACQUIRE", Severity.CRITICAL, "Slot concurrency violation.")
             return (None, self.report), 0.0

        try:
            # 1. Hydrate Raw Data
            files = SlotResolver.get_isolated_slot_files(self.slot)
            for key, path in files["core"].items():
                step_start = time.perf_counter()
                file_data = SaveLoader.hydrate_file(path, key)
                
                # [PH1-ENG-001] Logic Extraction: store only the JSON payload in the state
                self.raw_data[key] = file_data["payload"]
                
                duration = (time.perf_counter() - step_start) * 1000
                self.report.add_entry("FILE_HYDRATE", Severity.INFO, f"{key} hydrated and matched against schema.", duration)

            # 2. Semantic Analysis (Universal Root lookup)
            step_start = time.perf_counter()
            cs_payload = self.raw_data.get("CompleteSave", {})
            money = SchemaContract.get_nested_value(cs_payload, "SslValue.persistentProfileData.money")
            
            if money is not None and money < 0:
                duration = (time.perf_counter() - step_start) * 1000
                self.report.add_entry("SEMANTIC_FAIL", Severity.STRICT, f"Negative money ({money}) detected.", duration)
                raise SnowRunnerEngineError("Negative money is not allowed.")
            
            duration = (time.perf_counter() - step_start) * 1000
            self.report.add_entry("SEMANTIC_AUDIT", Severity.INFO, "Gameplay consistency verified.", duration)

            # 3. Derived State Projection [PH1-MAP-001]
            step_start = time.perf_counter()
            self._build_derived_state()
            duration = (time.perf_counter() - step_start) * 1000
            self.report.add_entry("DERIVED_PROJECTION", Severity.INFO, "Semantic mapping applied.", duration)

            # 4. Hash Generation (Bitstream Determinism) [PH1-DET-001]
            step_start = time.perf_counter()
            final_hash = HashEngine.compute_hash(self.raw_data)
            self.report.set_hash(final_hash)
            
            # [PH1-DET-002] State Binding: Attach hash to raw data before freezing
            self.raw_data["hash"] = final_hash
            
            duration = (time.perf_counter() - step_start) * 1000
            self.report.add_entry("HASH_COMPUTE", Severity.INFO, f"State hash bound: {final_hash[:12]}...", duration)

            # 4. Freeze & Context Build
            step_start = time.perf_counter()
            self.frozen_ctx = FrozenContext(self.raw_data)
            duration = (time.perf_counter() - step_start) * 1000
            self.report.add_entry("FREEZE_STATE", Severity.INFO, "Context locked.", duration)

            elapsed = (time.perf_counter() - start_time) * 1000
            self.report.set_total_time(elapsed)
            return (self.frozen_ctx, self.report), elapsed

        except Exception as e:
            logger.critical(f"PIPELINE_ERROR: {str(e)}")
            self.report.add_entry("PIPELINE_ABORT", Severity.CRITICAL, str(e))
            elapsed = (time.perf_counter() - start_time) * 1000
            self.report.set_total_time(elapsed)
            return (None, self.report), elapsed

        finally:
            slot_lock.release()
            logger.info(f"LOCK_RELEASED: Slot {self.slot.slot_index}")
