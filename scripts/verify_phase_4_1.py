# [PH4-VER-AUDIT] Phase 4.1 Global Verification Orchestrator (FIXED)
import sys
import os
import json

# Absolute Pathing
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "core_engineering")))

from maprunner.maprunner import MapRunner
from mapper.field_mapper import FieldMapper
from mapper.validators import FieldValidator
from engine.mutation_engine import MutationEngine
from verification.verifier import Verifier
from verification.chaos_engine import ChaosEngine
from verification.test_cases import TEST_CASES

def run_audit():
    print("Initializing Phase 4.1 Global Audit...")
    
    # 1. Foundation Load
    mpr = MapRunner()
    validator = FieldValidator(mpr)
    
    # 2. Verifier Initialization [PH4-VER-FIX]
    ver = Verifier(mpr, validator)
    chaos = ChaosEngine(ver.runner)
    
    # 3. Base State Initialization
    base_state = {
        "is_cross_session": True,
        "derived.player.money": 100,
        "derived.player.rank": 1,
        "CompleteSave.SslValue.persistentProfileData.trucksInWarehouse": [
            {"type": "ws_4964_white", "isUnlocked": True}
        ]
    }
    
    # 4. Matrix Execution [PH4-VER-MATRIX]
    print("\n--- STAGE 1: TEST MATRIX AUDIT ---")
    results = ver.run_all(base_state)
    
    # 5. Chaos Execution [PH4-VER-CHAOS]
    print("\n--- STAGE 2: CHAOS STRESS TEST (1000 iter) ---")
    chaos_results = chaos.run_chaos(base_state, TEST_CASES, iterations=1000)
    
    # 6. Regression Audit [PH4-VER-REG]
    print("\n--- STAGE 3: REGRESSION AUDIT ---")
    regression_results = ver.verify_regression(base_state, "initial_state")
    print(f"Regression Diff Count: {regression_results.get('diff_count', 'UNKNOWN')}")
    
    # 7. Final Scoring
    pass_count = sum(1 for r in results if r["status"] == "PASS")
    fail_count = len(results) - pass_count
    
    print("\n--- PHASE 4.1 AUDIT FINAL REPORT ---")
    print(f"Test Matrix: {pass_count} PASS, {fail_count} FAIL")
    print(f"Chaos Status: {chaos_results['status']}")
    print(f"Regression Parity: {'STABLE' if regression_results.get('diff_count') == 0 else 'DRIFT_DETECTED'}")

if __name__ == "__main__":
    run_audit()
