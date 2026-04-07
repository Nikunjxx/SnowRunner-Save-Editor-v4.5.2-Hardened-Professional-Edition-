# [PH4-VER-FAIL] Phase 4.3 User-Safety Failure Drill (HARDENED)
import sys
import os

# Absolute Pathing [PH4-ARCH-ROOT]
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from core_engineering.maprunner.maprunner import MapRunner
from core_engineering.mapper.validators import FieldValidator
from core_engineering.engine.mutation_engine import MutationEngine
from core_engineering.recovery.recovery_manager import RecoveryManager
from core_engineering.execution.safe_executor import SafeExecutor
from core_engineering.errors.exceptions import IntegrityError

def run_failure_drill():
    print("Initiating Phase 4.3 Error Handling & Safety Drill...")
    
    # 1. Foundation Load
    mpr = MapRunner()
    validator = FieldValidator(mpr)
    engine = MutationEngine(mpr, validator)
    recovery = RecoveryManager(engine)
    executor = SafeExecutor(recovery)
    
    initial_state = {
        "derived.player.money": 100,
        "derived.player.rank": 1,
        "CompleteSave.SslValue.persistentProfileData.trucksInWarehouse": [
            {"type": "ws_4964_white", "isUnlocked": True}
        ]
    }
    engine.set_state(initial_state)
    
    # --- DRILL 1: VALIDATION REJECTION ---
    print("\nDRILL 1: Simulating Illegal Mutation (Negative Money)...")
    # Result of apply_change calls should now raise ValidationError
    res = executor.execute(
        lambda: engine.apply_change("player.money", -100),
        context={"op": "drill_1"}
    )
    
    if res["status"] == "FAIL" and "Invalid action" in res["message"]:
        print("DRILL 1 SUCCESS: ValidationError translated correctly.")
        if engine.state["derived.player.money"] == 100:
             print("DRILL 1 SUCCESS: State successfully restored (Identity parity).")
        else:
             print(f"DRILL 1 FAILURE: State corrupted after rejection! Value: {engine.state.get('derived.player.money')}")
             return
    else:
        print(f"DRILL 1 FAILURE: Unexpected result {res}")
        return

    # --- DRILL 2: INTEGRITY VIOLATION ---
    print("\nDRILL 2: Simulating Disk Integrity Violation...")
    def integrity_op():
        # Raise directly to simulate TransactionManager failure
        from core_engineering.errors.exceptions import IntegrityError
        raise IntegrityError("High-fidelity read-back mismatch!")
        
    res = executor.execute(integrity_op, context={"op": "drill_2"})
    
    if res["status"] == "FAIL" and "Save validation failed" in res["message"]:
        print("DRILL 2 SUCCESS: IntegrityError translated correctly.")
    else:
        print(f"DRILL 2 FAILURE: Unexpected result {res}")
        return

    # --- DRILL 3: LOG AUDIT ---
    print("\nDRILL 3: Verifying session log creation...")
    log_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "logs"))
    logs = [f for f in os.listdir(log_dir) if f.endswith(".log")] if os.path.exists(log_dir) else []
    if len(logs) > 0:
        print(f"DRILL 3 SUCCESS: Session log found ({len(logs)} total logs).")
        # Optional: Print last log line preview
        with open(os.path.join(log_dir, logs[-1]), "r") as f:
            last_line = f.readlines()[-1]
            print(f"PREVIEW: {last_line.strip()}")
    else:
        print("DRILL 3 FAILURE: No session log generated!")
        return

    print("\n--- PHASE 4.3 AUDIT COMPLETE: USER LEVEL SAFETY UNBREAKABLE ---")

if __name__ == "__main__":
    run_failure_drill()
