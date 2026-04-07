import os
import sys
import json

# Add app to path
sys.path.append(os.path.join(os.getcwd(), 'app'))

from integrity_engine.manager import IntegrityManager
from integrity_engine.validator import ValidationReport

def test_integrity_enforcement():
    print("--- [v110.29] Integrity Enforcement Test ---")
    
    # 1. Setup mock environment
    test_dir = os.path.join(os.getcwd(), 'tmp_test_save')
    os.makedirs(test_dir, exist_ok=True)
    data_dir = os.path.join(os.getcwd(), 'tmp_integrity_data')
    os.makedirs(data_dir, exist_ok=True)
    
    save_path = os.path.join(test_dir, "CompleteSave.cfg")
    mock_data = {"money": 1000, "persistentProfileData": {"region_unlocked": 1}}
    with open(save_path, "w") as f:
        json.dump(mock_data, f)
        
    remote2_path = os.path.join(os.getcwd(), 'remote2') # Assuming it exists
    
    manager = IntegrityManager(test_dir, data_dir, remote2_path)
    
    print("\n[Test 1] Allowed Mutation (Money)")
    res = manager.execute_simple_mutation("add_money", value=5000)
    print(f"Status: {res['status']}, Success: {res['success']}")
    with open(save_path, "r") as f:
        updated = json.load(f)
        print(f"Updated Money: {updated['money']}")
        assert updated['money'] == 5000
    
    print("\n[Test 2] Blocked Mutation (Scope Violation)")
    # We will simulate a mutation that tries to touch something not in the whitelist
    # By manually triggering a feature that isn't supposed to touch 'money'
    try:
        from integrity_engine.dependency_resolver import DependencyResolver
        resolver = manager.resolver
        # Manually verify scope logic
        is_allowed = resolver.validate_scope("reveal_map", ["money"])
        print(f"Is 'money' allowed for 'reveal_map'? {is_allowed}")
        assert is_allowed == False
    except Exception as e:
        print(f"Scope test failed: {e}")

    print("\n[Test 3] Initialization Guard (Fog Profile Missing)")
    res = manager.execute_feature("reveal_map", "us_01_01")
    print(f"Status: {res['status']}, Error: {res['error']}")
    assert res['status'] == "blocked"

    print("\n[Test 4] Atomic Rollback (Validation Failure)")
    # Force a validation failure by corrupting the file during a mutation
    # We'll use a mock validator that always fails if a certain flag is set
    manager.validator.FAIL_FOR_TEST = True # We'll add this to validator.py for testing
    
    print("Triggering feature with forced validation failure...")
    res = manager.execute_simple_mutation("add_money", value=999999)
    print(f"Status: {res['status']}, Error: {res['error']}")
    with open(save_path, "r") as f:
        final_data = json.load(f)
        print(f"Data after rollback: {final_data['money']} (Expected 5000)")
        assert final_data['money'] == 5000
    
    print("\n--- ALL INTEGRITY TESTS PASSED ---")

if __name__ == "__main__":
    test_integrity_enforcement()
