# [PH4-VER-DEBUG] Debug Script for Verification Suite
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
from verification.test_cases import TEST_CASES

def debug_run():
    mpr = MapRunner()
    validator = FieldValidator(mpr)
    engine = MutationEngine(mpr, validator)
    mapper = FieldMapper(mpr)
    ver = Verifier(engine, mapper)
    
    base_state = {
        "is_cross_session": True,
        "derived.player.money": 100,
        "derived.player.rank": 1,
        "CompleteSave.SslValue.persistentProfileData.trucksInWarehouse": [
            {"type": "ws_4964_white", "isUnlocked": True}
        ]
    }
    
    results = ver.run_all(base_state)
    
    print("\n--- DETAILED FAILURE ANALYSIS ---")
    for r in results:
        if r["status"] != "PASS":
            print(f"\nTEST: {r['test']}")
            print(f"REASON: {r['reason']}")
            if "errors" in r:
                print(f"ERRORS: {json.dumps(r['errors'], indent=2)}")
            if "diff" in r:
                print(f"DIFF COUNT: {r['diff']['diff_count']}")

if __name__ == "__main__":
    debug_run()
