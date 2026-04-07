import os
import zlib
import json

def find_all_keys(data, keys_set, depth=0):
    if depth > 10: return
    if isinstance(data, dict):
        for k, v in data.items():
            keys_set.add(k)
            find_all_keys(v, keys_set, depth+1)
    elif isinstance(data, list):
        for item in data:
            find_all_keys(item, keys_set, depth+1)

def inspect_save():
    path = r"C:\Program Files (x86)\Steam\userdata\996096852\1465360\remote\CompleteSave.cfg"
    if not os.path.exists(path):
        print("File not found.")
        return

    with open(path, "rb") as f:
        raw = f.read()

    try:
        # Check if first char is '{'
        if raw[0] == 0x7b:
            payload = raw
        else:
            payload = zlib.decompress(raw[4:])
            
        data = json.loads(payload.decode('utf-8'))
        all_keys = set()
        find_all_keys(data, all_keys)
        
        print("=" * 60)
        print("KEY DISCOVERY REPORT")
        print("=" * 60)
        
        # Look for target candidates
        targets = ["money", "rank", "experience", "level", "finishedObjs", "unlockedMaps"]
        found = [k for k in all_keys if any(t.lower() in k.lower() for t in targets)]
        
        print(f"Total Unique Keys: {len(all_keys)}")
        print(f"Interest-Matched Keys: {len(found)}")
        for k in sorted(found):
            print(f"  - {k}")
            
    except Exception as e:
        print(f"FAIL: {e}")

if __name__ == "__main__":
    inspect_save()
