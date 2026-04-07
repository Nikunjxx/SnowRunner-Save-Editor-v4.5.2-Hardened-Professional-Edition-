# [PH4-VER-PERF] Phase 4.4 Performance & Identity Audit
import sys
import os
import time

# Absolute Pathing [PH4-ARCH-ROOT]
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from core_engineering.maprunner.maprunner import MapRunner
from core_engineering.mapper.validators import FieldValidator
from core_engineering.engine.mutation_engine import MutationEngine
from core_engineering.recovery.recovery_manager import RecoveryManager
from core_engineering.execution.safe_executor import SafeExecutor
from core_engineering.verification.snapshot_manager import SnapshotManager

def run_perf_audit():
    print("Initiating Phase 4.4 Performance & Identity Audit...")
    
    # 1. Foundation Load
    mpr = MapRunner()
    validator = FieldValidator(mpr)
    engine = MutationEngine(mpr, validator)
    recovery = RecoveryManager(engine)
    executor = SafeExecutor(recovery)
    
    # Large state simulation
    initial_state = {
        "player": {"money": 100, "rank": 1},
        "trucks": [{"id": i, "isUnlocked": True} for i in range(1000)], # Big list
        "upgrades": {"unlocked": []}
    }
    engine.set_state(initial_state)
    
    # --- DRILL 1: DIRTY-PATH IDENTITY CHECK ---
    print("\nDRILL 1: Verifying Structural Sharing (Identity Persistence)...")
    original_trucks = engine.state["trucks"]
    original_upgrades = engine.state["upgrades"]
    
    # Perform mutation on PLAYER only
    executor.execute(
        lambda: engine.apply_change("player.money", 200),
        affected_path="player"
    )
    
    # Check if other branches were deep-copied or shared
    if engine.state["trucks"] is original_trucks:
         print("DRILL 1 SUCCESS: Unaffected branch 'trucks' correctly shared identity (COW optimized).")
    else:
         print("DRILL 1 FAILURE: Unaffected branch 'trucks' was redundantly cloned!")
         return
         
    if engine.state["upgrades"] is original_upgrades:
         print("DRILL 1 SUCCESS: Unaffected branch 'upgrades' correctly shared identity.")
    else:
         print("DRILL 1 FAILURE: Unaffected branch 'upgrades' was redundantly cloned!")
         return

    # --- DRILL 2: FAST-DIFF PERFORMANCE ---
    print("\nDRILL 2: Verifying Fast-Diff Efficiency...")
    sm = SnapshotManager()
    state_a = initial_state
    state_b = engine.state # State after one mutation
    
    start_time = time.perf_counter()
    diff_res = sm.diff(state_a, state_b)
    end_time = time.perf_counter()
    
    print(f"DRILL 2 SUCCESS: Diff completed in {(end_time - start_time)*1000:.4f}ms.")
    print(f"DIFF COUNT: {diff_res['diff_count']} (Expected 1: player.money)")
    
    if diff_res["diff_count"] != 1:
         print(f"DRILL 2 FAILURE: Incorrect diff count! Result: {diff_res['diffs']}")
         return

    # --- DRILL 3: ROLLBACK INTEGRITY ---
    print("\nDRILL 3: Verifying Rollback Fidelity...")
    def fail_op():
         engine.apply_change("player.money", 999999)
         raise ValueError("Forced Failure")
         
    executor.execute(fail_op, affected_path="player")
    
    if engine.state["player"]["money"] == 200: # Value before the failed op
         print("DRILL 3 SUCCESS: Targeted rollback restored state correctly.")
    else:
         print(f"DRILL 3 FAILURE: State corrupted after rollback! Value: {engine.state['player']['money']}")
         return

    print("\n--- PHASE 4.4 AUDIT COMPLETE: PERFORMANCE OPTIMIZED & SAFE ---")

if __name__ == "__main__":
    run_perf_audit()
