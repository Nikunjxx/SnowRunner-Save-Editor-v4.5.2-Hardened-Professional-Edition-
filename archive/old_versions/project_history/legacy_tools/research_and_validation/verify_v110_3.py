import sys
import os

# Add app to path
sys.path.append(os.path.join(os.getcwd(), 'app'))

try:
    from snowrunner_editor import _peek_slot_metadata
    
    test_file = r"e:\Snow Runner New Tool\remote\CompleteSave.cfg"
    print(f"Testing Profiler Fix on {test_file}...")
    res = _peek_slot_metadata(test_file)
    print(f"Result: {res}")
    
    if res.get('money', 0) > 0:
        print("SUCCESS: Money detected!")
    else:
        print("FAILURE: Still $0.")
        
except Exception as e:
    print(f"Verification Error: {e}")
