import logging
from typing import Any, Dict, List, Set, Union
from exceptions import SchemaError

# Engine Configuration
SCHEMA_VERSION = "1.0"
logger = logging.getLogger("SchemaValidator")

# [PH1-SCH-001] File-Aware Path Requirements
# Format: "FileNickname": { "Path.To.Key": ExpectedType }
FILE_SCHEMA_MAP = {
    "CompleteSave": {
        "STRICT": {
            "CompleteSave.SslValue.persistentProfileData.money": int,
            "CompleteSave.SslValue.persistentProfileData.experience": int,
            "CompleteSave.SslValue.persistentProfileData.rank": int,
        },
        "OPTIONAL": {
            "CompleteSave.SslValue.persistentProfileData.discoveredWatchtowers": list,
        }
    },
    "CommonSslSave": {
        "STRICT": {},
        "OPTIONAL": {
             "CommonSslSave.SslValue.unlockedGarageLevelList": list,
             "CommonSslSave.discoveredWatchtowers": list,
        }
    }
}

class SchemaContract:
    """
    Refined File-Aware Path Validator for SnowRunner.
    Ensures each file is audited against its specific contract.
    """
    
    @staticmethod
    def get_nested_value(data: Dict[str, Any], path: str) -> Any:
        """
        Helper to traverse a nested dict using dot-notation.
        [PH1-SCH-003] Root-Key Agnosticism.
        If the first path segment matches the root key of the data, it is skipped.
        """
        keys = path.split(".")
        val = data
        
        # Root-Key Agnosticism: SnowRunner slots use variants like CompleteSave, CompleteSave1, etc.
        root_keys = [rk for rk in data.keys() if rk not in ["cfg_version"]]
        if keys and len(root_keys) == 1:
             first_key = root_keys[0]
             # Match if path starts with the core filename (CompleteSave or CommonSslSave)
             if ("CompleteSave" in keys[0] and "CompleteSave" in first_key) or \
                ("CommonSslSave" in keys[0] and "CommonSslSave" in first_key):
                  val = data[first_key]
                  keys = keys[1:]

        for k in keys:
            if isinstance(val, dict) and k in val:
                val = val[k]
            else:
                return None
        return val

    @classmethod
    def validate(cls, payload: Dict[str, Any], file_nickname: str) -> bool:
        """
        [PH1-SCH-002] File-Bound Path Audit.
        Verifies existence and type safety per file contract.
        """
        logger.info(f"PH1-SCH-001: Initiating file-bound audit for {file_nickname}")
        
        contract = FILE_SCHEMA_MAP.get(file_nickname)
        if not contract:
            logger.warning(f"SCHEMA_BYPASS: No schema defined for {file_nickname}. Skipping deep audit.")
            return True

        # 1. Verify STRICT Requirements
        missing_required = []
        type_mismatches = []
        
        for path, expected_type in contract.get("STRICT", {}).items():
            val = cls.get_nested_value(payload, path)
            if val is None:
                missing_required.append(path)
            elif not isinstance(val, expected_type):
                type_mismatches.append(f"{path} (expected {expected_type.__name__}, got {type(val).__name__})")

        if missing_required or type_mismatches:
            error_msg = f"SCHEMA_CRITICAL_FAIL: {file_nickname} failed validation. "
            if missing_required: error_msg += f"Missing: {missing_required}. "
            if type_mismatches: error_msg += f"Types: {type_mismatches}."
            
            logger.critical(error_msg)
            raise SchemaError(error_msg)

        # 2. Audit OPTIONAL Requirements
        for path, expected_type in contract.get("OPTIONAL", {}).items():
            val = cls.get_nested_value(payload, path)
            if val is not None and not isinstance(val, expected_type):
                logger.warning(f"SCHEMA_WARN: Type mismatch for optional '{path}' (expected {expected_type.__name__}).")

        logger.info(f"SCHEMA_SUCCESS: {file_nickname} audit PASSED.")
        return True
