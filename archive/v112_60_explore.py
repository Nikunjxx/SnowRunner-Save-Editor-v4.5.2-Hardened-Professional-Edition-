import os
import sys
import json

# Ensure project modules are in path
sys.path.append(r"e:\Snow Runner New Tool")

from integrity_engine.manager import IntegrityManager

def explore_schema():
    target = r"C:\Program Files (x86)\Steam\userdata\996096852\1465360\remote"
    path = os.path.join(target, "CompleteSave.cfg")
    
    data_dir = os.path.join(os.environ['USERPROFILE'], "snowrunner_save_editor_data")
    manager = IntegrityManager(target, data_dir, target)
    
    header, payload = manager.zlib_handler.read(path)
    data = manager._resilient_json_load(payload)
    
    print("=" * 60)
    print("GLOBAL SCHEMA EXPLORATION")
    print("=" * 60)
    
    if not isinstance(data, dict):
        print(f"FAILED: Data is {type(data)}, not dict.")
        return

    for k1, v1 in data.items():
        print(f"+ {k1}")
        if isinstance(v1, dict):
            for k2 in v1.keys():
                print(f"  - {k2}")
        elif isinstance(v1, list):
            print(f"  [List of {len(v1)} items]")

if __name__ == "__main__":
    explore_schema()
