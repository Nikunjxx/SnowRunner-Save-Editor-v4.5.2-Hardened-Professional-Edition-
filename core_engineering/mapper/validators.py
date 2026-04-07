# [PH3-VAL-001] Safe Interaction Validators (REFINED FINAL)
from typing import Any, Tuple, Optional, Dict

class FieldValidator:
    """
    Validation layer for safe user edits.
    Consults MapRunner Knowledge for game-logic enforcement.
    """
    
    def __init__(self, maprunner):
        self.maprunner = maprunner

    def validate_money(self, new_money: Any) -> Tuple[bool, str]:
        """Ensures funds are within logical game limits."""
        try:
            val = int(new_money)
            # [PH3-VAL-002] Explicit Rule Enforcement
            if 0 <= val <= 999999999:
                return True, "Valid funds."
            return False, f"Rule: Money ({val}) out of bounds. Expected 0-999M."
        except (ValueError, TypeError):
            return False, f"Rule: Money '{new_money}' is not a valid integer."

    def validate_truck_unlock(self, truck_id: str, new_value: bool, context: Dict[str, Any]) -> Tuple[bool, str]:
        """
        Ensures that unlocking a truck is safe (no regression unless context-bound).
        Follows Phase 2 'CONDITIONAL_LOCK' logic.
        """
        truck = self.maprunner.get_truck(truck_id)
        if not truck:
            return False, f"Error: Identity Resolve Failed. Truck ID: {truck_id} unknown."
            
        # [PH3-VAL-003] Explicit Condition Filtering
        # If turning from Unlocked -> Locked, check for session context.
        if new_value is False:
            if not context.get("is_cross_session"):
                return False, f"Rule: [CONDITIONAL_LOCK] Regression for {truck.name} rejected within the same session."
            return True, f"Operation: [CROSS_SESSION] Lock for {truck.name} approved."
        
        # Explicitly approve Unlocks
        if new_value is True:
            return True, f"Operation: Unlock for {truck.name} approved."
        
        # [REFINEMENT] No Default True Fallback
        return False, f"Error: Unknown operation value '{new_value}' for truck {truck_id}."

    def validate_upgrade_availability(self, truck_id: str, upgrade_id: str) -> Tuple[bool, str]:
        """Cross-references the truck with supported upgrades from MapRunner registry."""
        upgrades = self.maprunner.get_upgrades(truck_id)
        supported_ids = [upg.id for upg in upgrades]
        
        if upgrade_id in supported_ids:
            return True, f"Rule: Upgrade {upgrade_id} is compatible."
        
        # [REFINEMENT] Explicit rejection if no match
        return False, f"Rule: [INVALID_PART] Part {upgrade_id} is NOT compatible with vehicle {truck_id}."
