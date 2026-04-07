import os
import sys
import json

# Add app to path
sys.path.append(os.path.join(os.getcwd(), 'app'))

from integrity_engine.manager import IntegrityManager

def test_v110_31_batch():
    print("Testing v110.31 Growth Phase 1: Integrity Engine Batch & Objectives")
    
    # Setup dummy save folder
    test_dir = os.path.join(os.getcwd(), "tmp", "test_v110_31")
    os.makedirs(test_dir, exist_ok=True)
    
    save_path = os.path.join(test_dir, "CompleteSave.cfg")
    dummy_data = {
        "CompleteSave": {
            "SslValue": {
                "is_initialized": True,
                "objectiveStates": {},
                "finishedObjs": []
            }
        }
    }
    with open(save_path, "w") as f:
        json.dump(dummy_data, f)
    
    manager = IntegrityManager(test_dir)
    manager.dry_run = True # Safety first
    
    # 1. Test Preview
    print("\n--- Testing Preview ---")
    preview = manager.preview_feature_execution("complete_objective", region="US_01_01", objective_id="OBJ_MICHIGAN_01")
    for step in preview:
        print(f"Preview Step: {step}")
    
    # 2. Test Batch Execution
    print("\n--- Testing Batch Execution ---")
    batch_items = [
        {"objective_id": "OBJ_1", "region": "US_01_01"},
        {"objective_id": "OBJ_2", "region": "US_01_02"}
    ]
    res = manager.execute_feature_batch("complete_objective", batch_items)
    
    print(f"Status: {res['status']}")
    print(f"Processed: {res['processed']}")
    if res['report']:
        print(f"Structural Integrity: {'SAFE' if res['report'].is_safe else 'CORRUPT'}")

if __name__ == "__main__":
    test_v110_31_batch()
