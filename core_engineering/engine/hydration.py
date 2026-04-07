import json
import logging
from typing import Any, Dict, List, Optional, Tuple
from exceptions import IntegrityError, SchemaError
from schema import SchemaContract
from slot_resolver import SlotContext, SlotResolver

logger = logging.getLogger("HydrationEngine")

class FrozenContext:
    """
    Immutable wrapper for the save game context.
    Prevents accidental state mutation outside the Transaction Layer.
    """
    def __init__(self, data: Dict[str, Any]):
        self._data = data
        self._frozen = True

    @property
    def state(self) -> Dict[str, Any]:
        """Provides a read-only logical view of the entire context state."""
        return self.to_dict()

    def __getattr__(self, name: str) -> Any:
        # [PH2-HYD-001] Recursive Dot-Access Support
        val = self._data.get(name)
        if isinstance(val, dict):
            return FrozenContext(val)
        return val

    def __setattr__(self, name: str, value: Any):
        # Use __dict__ lookup directly to avoid triggered __getattr__ recursion
        if "_frozen" in self.__dict__ and self.__dict__["_frozen"]:
            raise AttributeError("CONTEXT_IMMUTABLE: State cannot be modified directly.")
        super().__setattr__(name, value)

    def to_dict(self) -> Dict[str, Any]:
        # Return a copy to ensure the internal state remains safe
        return json.loads(json.dumps(self._data))

class SaveLoader:
    """
    Strict zero-trust hydration engine.
    Mandates: Null-terminator check, UTF-8 safety, Schema audit.
    """

    @staticmethod
    def read_safe(file_path: str) -> Tuple[bytes, str]:
        """
        Reads a file with strict bit-level and encoding checks.
        Returns (original_bytes, decoded_text).
        """
        with open(file_path, "rb") as f:
            raw_data = f.read()

        # 1. Null Terminator Enforcement
        if not raw_data.endswith(b"\x00"):
            logger.critical(f"INTEGRITY_FAIL: {file_path} missing null terminator.")
            raise IntegrityError(f"Missing mandatory null terminator in {file_path}")

        # 2. Encoding Safety (UTF-8 with Replace)
        try:
            # Game uses UTF-8 usually, but we strip the null for JSON parsing
            text_data = raw_data[:-1].decode("utf-8", errors="replace")
            
            # Validation: Ensure no data loss in critical strings
            # (Checking if re-encoding matches helps detect major corruption)
            re_encoded = text_data.encode("utf-8")
            if len(re_encoded) < (len(raw_data) - 1) * 0.9: # Threshold for major loss
                 raise IntegrityError("Significant data loss during UTF-8 decoding.")
                 
        except Exception as e:
            raise IntegrityError(f"Encoding failure in {file_path}: {str(e)}")

        return raw_data, text_data

    @classmethod
    def hydrate_file(cls, file_path: str, nickname: str) -> Dict[str, Any]:
        """Hydrates a single JSON-based cfg file with schema verification."""
        raw_bytes, text_content = cls.read_safe(file_path)
        
        try:
            payload = json.loads(text_content)
        except json.JSONDecodeError as e:
            logger.error(f"JSON_SYNTAX_ERROR in {nickname}: {str(e)}")
            raise IntegrityError(f"Syntax error in {nickname}: {str(e)}")

        # Schema Audit (Tolerant Strictness)
        SchemaContract.validate(payload, nickname)
        
        # [PH1-HYD-002] Root Transparency: Unwrap the redundant filename key
        # SnowRunner JSON files wrap everything in a key matching the filename (e.g. CompleteSave)
        # We unwrap this to make the state logical and Root-Key Agnostic.
        unwrapped = payload
        root_keys = [rk for rk in payload.keys() if rk not in ["cfg_version"]]
        if len(root_keys) == 1:
            root_key = root_keys[0]
            if nickname in root_key or root_key in nickname:
                unwrapped = payload[root_key]
                # Preserve cfg_version if it existed at root
                if "cfg_version" in payload and isinstance(unwrapped, dict):
                    unwrapped["cfg_version"] = payload["cfg_version"]

        return {
            "payload": unwrapped,
            "raw": raw_bytes
        }

class EngineContext:
    """
    High-level manager for a complete Slot data set.
    """
    def __init__(self, slot: SlotContext):
        self.slot = slot
        self.files: Dict[str, Dict[str, Any]] = {}
        self.is_valid = False

    def load_all(self):
        """
        [PH1-HYD-001] Full Slot Hydration.
        Partial Hydration Guard: Aborts completely if any one file fails.
        """
        logger.info(f"Initiating Slot {self.slot.slot_index} Hydration...")
        
        file_map = SlotResolver.get_isolated_slot_files(self.slot)
        
        try:
            # 1. Hydrate Core Files (CompleteSave, CommonSslSave)
            for key, path in file_map["core"].items():
                self.files[key] = SaveLoader.hydrate_file(path, key)
            
            # 2. Cache Binary Paths (STS, Fog) for Phase 5
            # We don't hydrate bytes here, just preserve paths for the session
            self.files["sts_paths"] = file_map["sts"]
            self.files["fog_paths"] = file_map["fog"]
            
            self.is_valid = True
            logger.info(f"Slot {self.slot.slot_index} Hydration SUCCESS.")
            
        except Exception as e:
            logger.critical(f"SLOT_HYDRATION_ABORTED: {str(e)}")
            self.is_valid = False
            self.files = {} # Wipe partial data
            raise
