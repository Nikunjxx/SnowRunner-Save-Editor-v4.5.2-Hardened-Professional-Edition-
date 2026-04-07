import os
import sys
import json

# Add app to path
sys.path.append(os.path.join(os.getcwd(), 'app'))

from integrity_engine.manager import IntegrityManager
from integrity_engine.dependency_resolver import DependencyResolver

def smoke_test():
    print("--- Integrity System Smoke Test ---")
    
    # Setup
    test_dir = os.path.join(os.getcwd(), 'tmp_test_save')
    os.makedirs(test_dir, exist_ok=True)
    data_dir = os.path.join(os.getcwd(), 'tmp_integrity_data')
    os.makedirs(data_dir, exist_ok=True)
    
    save_path = os.path.join(test_dir, "CompleteSave.cfg")
    with open(save_path, "w") as f:
        json.dump({"money":100, "rank":1, "experience":0}, f)
        
    resolver = DependencyResolver(os.path.join(data_dir, "ref.json"))
    
    print("1. Testing Scope Enforcement (Money vs Reveal Map)")
    # Money is ALLOWED for 'add_money'
    assert resolver.validate_scope("add_money", ["money"]) == True
    # Money is BLOCKED for 'reveal_map'
    assert resolver.validate_scope("reveal_map", ["money"]) == False
    print("   Scope enforcement: OK")
    
    print("2. Testing Placeholder Resolution")
    whitelist, mutations = resolver.resolve("add_money", "GLOBAL", value=5000)
    # Check if value 5000 is in mutations
    found = False
    for m in mutations:
        if m.get("key") == "money" and m.get("value") == 5000:
            found = True
    assert found == True
    print("   Placeholder resolution: OK")
    
    print("\n--- SMOKE TEST PASSED ---")

if __name__ == "__main__":
    smoke_test()
