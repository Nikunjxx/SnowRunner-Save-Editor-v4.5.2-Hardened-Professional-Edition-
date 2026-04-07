import json
import os

def load_steam_cfg(path):
    with open(path, "rb") as f:
        data = f.read()
    # Remove the extra byte at the end and decode
    clean_json = data[:-1].decode("utf-8")
    return json.loads(clean_json)

def probe():
    root = r"E:\Snow Runner New Tool\test_data\steam_live_mirror"
    cs_path = os.path.join(root, "CompleteSave.cfg")
    ssl_path = os.path.join(root, "CommonSslSave.cfg")
    
    if not os.path.exists(cs_path) or not os.path.exists(ssl_path):
        print("Missing required files for probe.")
        return

    cs = load_steam_cfg(cs_path)
    ssl = load_steam_cfg(ssl_path)
    
    # 1. CompleteSave Structure
    # Root key is "CompleteSave"
    profile = cs.get("CompleteSave", {}).get("SslValue", {}).get("persistentProfileData", {})
    print("CompleteSave Profile Keys:", sorted(list(profile.keys())))
    print(f"Money: {profile.get('money')}, Experience: {profile.get('experience')}, Rank: {profile.get('rank')}")

    # 2. CommonSslSave Structure
    # Root key is "CommonSslSave"
    common = ssl.get("CommonSslSave", {}).get("SslValue", {})
    print("\nCommonSslSave Keys:", sorted(list(common.keys())))
    
    # Identify overlaps
    shared = set(profile.keys()).intersection(set(common.keys()))
    print("\nPotential Shared Fields (Direct Collision):", sorted(list(shared)))

if __name__ == "__main__":
    probe()
