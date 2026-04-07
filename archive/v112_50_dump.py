import os
import sys
import json

# Ensure project modules are in path
sys.path.append(r"e:\Snow Runner New Tool")

from integrity_engine.manager import IntegrityManager

def test_json_content():
    target = r"C:\Program Files (x86)\Steam\userdata\996096852\1465360\remote"
    path = os.path.join(target, "CompleteSave.cfg")
    
    data_dir = os.path.join(os.environ['USERPROFILE'], "snowrunner_save_editor_data")
    manager = IntegrityManager(target, data_dir, target)
    
    print("=" * 60)
    print("STEAM JSON CONTENT DUMP")
    print("=" * 60)
    
    header, payload = manager.zlib_handler.read(path)
    data = manager._resilient_json_load(payload)
    
    if not data:
        print("FAILED: No JSON data extracted.")
        return

    print(f"Top-level Keys: {list(data.keys())}")
    
    # Dump a sample of PersistentPlayerInfo if found
    p_info = manager._find_key_recursive(data, "PersistentPlayerInfo")
    if p_info:
        print("-" * 30)
        print("PersistentPlayerInfo Content:")
        # Convert to string and show first 500 chars
        print(json.dumps(p_info, indent=2)[:1000])
    else:
        print("FAILED: PersistentPlayerInfo key NOT FOUND recursively.")
        
if __name__ == "__main__":
    test_json_content()
