import os
import sys
import json

# Ensure project modules are in path
sys.path.append(r"e:\Snow Runner New Tool")

from integrity_engine.manager import IntegrityManager

def snapshot_schema():
    target = r"C:\Program Files (x86)\Steam\userdata\996096852\1465360\remote"
    path = os.path.join(target, "CompleteSave.cfg")
    
    data_dir = os.path.join(os.environ['USERPROFILE'], "snowrunner_save_editor_data")
    manager = IntegrityManager(target, data_dir, target)
    
    header, payload = manager.zlib_handler.read(path)
    data = manager._resilient_json_load(payload)
    
    print("=" * 60)
    print("STEAM SCHEMA SNAPSHOT")
    print("=" * 60)
    
    # Try to find something that looks like money by scanning raw text too
    text = payload.decode('utf-8', errors='replace')
    print(f"Raw Text Sample (First 1000): {text[:1000]}")
    
    print("-" * 30)
    print(f"Parsed Dict Type: {type(data)}")
    if isinstance(data, dict):
        print(f"Parsed Keys: {list(data.keys())[:20]}")
        # Look for SslValue content
        if "PersistentPlayerInfo" in data:
            print("PersistentPlayerInfo FOUND AT ROOT of peeled data.")
        else:
            print("PersistentPlayerInfo NOT found at root of peeled data.")

if __name__ == "__main__":
    snapshot_schema()
