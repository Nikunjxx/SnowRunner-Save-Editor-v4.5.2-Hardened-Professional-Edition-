# [PH4-INT-005] Transactional Save Core
import os
import shutil
import tempfile
from datetime import datetime
from typing import Any, Dict
from core_engineering.verification.snapshot_manager import SnapshotManager
from core_engineering.verification.invariants import InvariantChecker
from core_engineering.errors.exceptions import IntegrityError, TransactionError

class SaveTransactionManager:
    """
    Heart of Phase 4.2.
    Orchestrates the Write-Validate-Commit-Rollback loop.
    Ensures 100% mission safety for disk operations.
    """
    
    def __init__(self, adapter):
        self.adapter = adapter

    def execute(self, file_path: str, new_state: Dict[str, Any]) -> Dict[str, Any]:
        """
        Transactional execution for absolute safety.
        ORDER: 1. BACKUP -> 2. TEMP_WRITE -> 3. VALIDATE -> 4. ATOMIC_COMMIT
        """
        if not os.path.exists(file_path):
             return {"status": "FAILED", "reason": f"Target file not found: {file_path}"}
             
        # [PH4-SEC-BACK] Timestamped Traceable Backup
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_path = f"{file_path}_{timestamp}.bak"
        temp_path = None
        
        try:
            # STEP 1: FORCE BACKUP [PH4-SEC-001]
            shutil.copy(file_path, backup_path)
            
            # STEP 2: WRITE TO TEMP FILE [PH4-SEC-002]
            # Ensure temp file is on the same drive for atomic replace
            temp_dir = os.path.dirname(os.path.abspath(file_path))
            with tempfile.NamedTemporaryFile(dir=temp_dir, delete=False) as tmp:
                temp_path = tmp.name
                
            self.adapter.write(temp_path, new_state)
            
            # STEP 3: HIGH-FIDELITY READ-BACK VALIDATION [PH4-SEC-003]
            # [GAP-1/3/5 Reconciliation]
            validated_state = self.adapter.read(temp_path)
            
            if not self._validate_integrity(new_state, validated_state):
                 raise IntegrityError("High-fidelity read-back validation failed. Bit-drift or encoding mismatch detected.")
                 
            # STEP 4: ATOMIC COMMIT [PH4-SEC-004]
            # Replace the original with the validated temp file
            os.replace(temp_path, file_path)
            
            return {"status": "COMMITTED", "path": file_path}
            
        except Exception as e:
            # STEP 5: AUTOMATIC ROLLBACK [PH4-SEC-005]
            if os.path.exists(backup_path):
                shutil.copy(backup_path, file_path)
            
            # Cleanup temp if it exists
            if temp_path and os.path.exists(temp_path):
                os.remove(temp_path)
                
            return {
                "status": "ROLLED_BACK",
                "error": str(e)
            }

    def _validate_integrity(self, expected: Dict[str, Any], actual: Dict[str, Any]) -> bool:
        """
        [PH4-SEC-003] Absolute Parity Audit.
        Verifies that the written bytes actually represent the intended state.
        """
        # 1. Structural/Semantic Diffs
        diff = SnapshotManager.diff(expected, actual)
        if diff["diff_count"] != 0:
            return False
            
        # 2. Invariant Engine Audit
        errors = InvariantChecker.validate(actual)
        if errors:
            return False
            
        return True
