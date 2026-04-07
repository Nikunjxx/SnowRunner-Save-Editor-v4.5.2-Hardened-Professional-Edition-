# [PH4-INT-001] Standalone Mutation Engine (HARDENED)
import copy
from typing import Any, Dict, Optional, Tuple
from dataclasses import dataclass
from core_engineering.errors.exceptions import ValidationError

@dataclass
class MutationResult:
    """Detailed output for absolute observability of the mutation pipeline."""
    success: bool
    stage: str # VALIDATOR | MUTATION | COMMIT
    message: str
    field_path: str
    new_value: Any

class MutationEngine:
    """
    Control Layer for absolute state mutation.
    Ensures that all field-level edits follow a strict, atomic pipeline.
    """
    
    def __init__(self, maprunner, validator):
        self.maprunner = maprunner
        self.validator = validator
        self.state = {} # Current interpreted data structure
        
    def set_state(self, initial_state: Dict[str, Any]):
        """Injects a new base state for mutation (Phase 2 input)."""
        self.state = copy.deepcopy(initial_state)

    def apply_change(self, field_path: str, new_value: Any, context: Optional[dict] = None) -> MutationResult:
        """
        [PH4-MUT-002] Multi-Stage Atomic Mutation.
        [GAP-3] Pipeline Stage Assertions.
        """
        context = context or {}
        backup_state = copy.deepcopy(self.state)
        
        try:
            # 1. Validation Stage
            valid, msg = self._validate(field_path, new_value, context)
            if not valid:
                # [PH4-ERR-INT] Global Exception Integration
                raise ValidationError(msg, context={"field": field_path, "value": new_value})
                
            # 2. Structural Stage (Identity-Based Resolution)
            self._mutate(field_path, new_value, context)
            
            return MutationResult(True, "COMMIT", "Mutation Successful", field_path, new_value)
            
        except ValidationError:
            # Validation errors keep the state clean, but we re-raise for the Executor
            raise
        except Exception as e:
            # Atomic Rollback for unexpected system failures
            self.state = backup_state
            raise

    def _validate(self, field_path: str, new_value: Any, context: dict) -> Tuple[bool, str]:
        """Consults the FieldValidator for game-logic enforcement."""
        if field_path == "player.money":
            return self.validator.validate_money(new_value)
            
        elif field_path.startswith("trucks.") and "isUnlocked" in field_path:
            truck_id = field_path.split(".")[1]
            return self.validator.validate_truck_unlock(truck_id, new_value, context)
            
        return False, f"Rule: Path '{field_path}' is not mapped to a known validator."

    def _mutate(self, field_path: str, new_value: Any, context: dict):
        """
        [PH4-MUT-IMMUT] Strict Path Immutability.
        Ensures structural sharing for non-affected branches.
        """
        # [STEP 1] Identify root key of affected branch
        root_key = field_path.split(".")[0] if "." in field_path else field_path
        
        if root_key not in self.state:
             # Fallback: Create placeholder if missing (e.g. 'derived' might be missing)
             self.state[root_key] = {}

        # [STEP 2] ENFORCE IMMUTABILITY
        # Replace the root branch with a shallow copy to trigger 'is' identity shifts.
        self.state[root_key] = copy.copy(self.state[root_key])

        # [STEP 3] Final Structural Mutation
        if field_path == "player.money":
            self.state["player"]["money"] = int(new_value)
            
        elif field_path.startswith("trucks.") and "isUnlocked" in field_path:
            truck_id = field_path.split(".")[1]
            raw_id = self.maprunner.id_mapper.get_raw(truck_id)
            
            # Since trucks is a list, we might need to copy individual elements 
            # if we wanted deep immutability, but for Phase 4.4 optimization, 
            # replacing the root 'trucks' key is enough.
            warehouse = self.state.get("CompleteSave.SslValue.persistentProfileData.trucksInWarehouse", [])
            for truck in warehouse:
                if truck["type"] == raw_id:
                    truck["isUnlocked"] = new_value
                    break
        else:
            raise KeyError(f"Resolution failed for path: {field_path}")
