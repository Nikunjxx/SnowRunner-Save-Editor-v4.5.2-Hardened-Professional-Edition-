import json
import os

def load_steam_cfg(path):
    with open(path, "rb") as f:
        data = f.read()
    clean_json = data[:-1].decode("utf-8")
    return json.loads(clean_json)

def compare_slots():
    root = r"E:\Snow Runner New Tool\test_data\steam_live_mirror"
    p0 = os.path.join(root, "CompleteSave.cfg")
    p1 = os.path.join(root, "CompleteSave1.cfg")
    
    if not os.path.exists(p0) or not os.path.exists(p1):
        print("Missing slots for comparison.")
        return

    c0 = load_steam_cfg(p0)
    c1 = load_steam_cfg(p1)
    
    prof0 = c0.get("CompleteSave", {}).get("SslValue", {}).get("persistentProfileData", {})
    prof1 = c1.get("CompleteSave1", {}).get("SslValue", {}).get("persistentProfileData", {})
    
    # 1. Structural Comparison
    keys0 = set(prof0.keys())
    keys1 = set(prof1.keys())
    
    print("Keys missing in Slot 1:", sorted(list(keys0 - keys1)))
    print("Keys missing in Slot 0:", sorted(list(keys1 - keys0)))
    
    # 2. Value Comparison (Baseline)
    common = sorted(list(keys0.intersection(keys1)))
    mismatches = []
    for k in common:
        if prof0[k] != prof1[k]:
            mismatches.append(k)
    
    print("\nValue Mismatches in common fields:", mismatches)
    for k in mismatches[:5]:
        v0 = prof0[k]
        v1 = prof1[k]
        print(f"  Field: {k}")
        print(f"    Slot 0: {type(v0)} (sample: {str(v0)[:50]})")
        print(f"    Slot 1: {type(v1)} (sample: {str(v1)[:50]})")

if __name__ == "__main__":
    compare_slots()
