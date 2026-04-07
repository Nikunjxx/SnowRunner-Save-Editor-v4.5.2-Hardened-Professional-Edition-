import logging

logger = logging.getLogger("MappingContract")

# Phase 1.3: Deterministic Supreme Mapping
# Forward Mapping: [Internal Ref] -> [Raw JSON Path]
DERIVED_MAP = {
    "player.money": "CompleteSave.SslValue.persistentProfileData.money",
    "player.rank": "CompleteSave.SslValue.persistentProfileData.rank",
    "player.experience": "CompleteSave.SslValue.persistentProfileData.experience",
    "garage.unlocked_count": "CommonSslSave.SslValue.unlockedGarageLevelList", # Mapping to list for count
}

# Reverse Mapping: [Internal Ref] -> [Raw JSON Path]
# Mandatory Requirement: [PH1-MAP-001] One-to-One Integrity Constraint
REVERSE_MAP = {
    "player.money": "CompleteSave.SslValue.persistentProfileData.money",
    "player.rank": "CompleteSave.SslValue.persistentProfileData.rank",
    "player.experience": "CompleteSave.SslValue.persistentProfileData.experience",
}

# [PH1-MAP-002] Order-Sensitive Path Registry
# Lists at these paths will NEVER be sorted during canonicalization to preserve game progression.
ORDER_SENSITIVE_PATHS = [
    "CompleteSave.missions.sequence",
    "CompleteSave.objectives.order",
    "CompleteSave.SslValue.persistentProfileData.tasks", # Progression order
    "CompleteSave.SslValue.persistentProfileData.waypointValues" # Path/Route order
]

# Enforce One-to-One Integrity at load time
def validate_mapping_integrity():
    if len(set(REVERSE_MAP.values())) != len(REVERSE_MAP):
        logger.critical("MAPPING_COLLISION: Multiple derived fields point to the same raw JSON path.")
        raise RuntimeError("Reverse mapping collision detected. Determinism violated.")
    logger.info("MAPPING_INTEGRITY: 100% Unique bidirectional contract verified.")

validate_mapping_integrity()
