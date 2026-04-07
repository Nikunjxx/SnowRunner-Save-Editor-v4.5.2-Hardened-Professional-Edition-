import os
import zlib
import json

def resilient_load(path):
    if not os.path.exists(path): return None
    with open(path, "rb") as f:
        raw = f.read()
    if not raw: return None
    
    # Toggle ZLIB/Plain
    try:
        if raw[0] == 0x7b: # '{'
            payload = raw
        else:
            payload = zlib.decompress(raw[4:])
            
        text = payload.decode('utf-8')
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            import json
            decoder = json.JSONDecoder()
            obj, _ = decoder.raw_decode(text)
            return obj
    except:
        return None

def find_key(data, target):
    if not isinstance(data, (dict, list)): return None
    t_low = target.lower()
    if isinstance(data, dict):
        for k, v in data.items():
            if k.lower() == t_low: return v
            res = find_key(v, target)
            if res: return res
    elif isinstance(data, list):
        for item in data:
            res = find_key(item, target)
            if res: return res
    return None

def analyze_all():
    base = r"C:\Program Files (x86)\Steam\userdata\996096852\1465360\remote"
    print("="*60)
    print("DEEP ANALYSIS OF STEAM REMOTE FOLDER")
    print("="*60)
    
    files = ["CompleteSave.cfg", "CompleteSave1.cfg", "CommonSslSave.cfg"]
    for f in files:
        path = os.path.join(base, f)
        data = resilient_load(path)
        if not data:
            print(f"[-] {f}: FAILED TO LOAD/DECODE")
            continue
            
        print(f"[+] {f}: LOADED")
        gt = find_key(data, "gameTime")
        money = find_key(data, "money")
        rank = find_key(data, "rank")
        unlocked = find_key(data, "unlockedMaps")
        
        print(f"    - GameTime: {gt if gt else 'Not found'}")
        print(f"    - Money: {money if money else 0}")
        print(f"    - Rank: {rank if rank else 0}")
        print(f"    - Unlocked Maps: {len(unlocked) if unlocked else 0}")

    # STS HEX DUMP
    sts_file = os.path.join(base, "sts_level_us_01_01.cfg")
    if os.path.exists(sts_file):
        with open(sts_file, "rb") as f:
            raw = f.read(64)
        print("-" * 30)
        print(f"[STS] {os.path.basename(sts_file)} Magic:")
        print(f"    Hex: {raw.hex(' ')}")

if __name__ == "__main__":
    analyze_all()
