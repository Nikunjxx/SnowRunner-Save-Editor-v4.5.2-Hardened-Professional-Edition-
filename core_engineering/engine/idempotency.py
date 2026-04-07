import logging
from typing import Dict, Any, List
from intent import Intent

logger = logging.getLogger("IdempotencyGuard")

# [PH1-IDM-001] Multi-Field Aware State-Based Check
# Idempotency is defined by the CURRENT STATE, not the Operation ID.
def check_state_idempotency(intent: Intent, ctx_derived: Dict[str, Any]) -> bool:
    """
    Checks if all target values in the intent are already 
    reflected in the derived state.
    Returns True if already fulfilled.
    """
    if not intent.target_values:
        return True # Empty intent is already applied

    all_matched = True
    for path, target_value in intent.target_values.items():
        # Traverse the derived state to match the path
        if ctx_derived.get(path) != target_value:
            all_matched = False
            break

    if all_matched:
        logger.info(f"IDEMPOTENCY_MATCH: Intent {intent.category} is already fulfilled.")
    return all_matched

# [PH1-IDM-002] Path-Level Check (Granular)
def check_field_idempotency(path: str, value: Any, ctx_derived: Dict[str, Any]) -> bool:
    return ctx_derived.get(path) == value
