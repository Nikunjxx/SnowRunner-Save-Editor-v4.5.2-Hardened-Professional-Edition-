import os
import zlib
import json

def d(p):
    print(f"Analyzing {p}...")
    with open(p, "rb") as f:
        r = f.read()
    
    # 1. Try plain JSON (CompleteSave)
    try:
        # Use a more lenient decode or just check start
        start = r[:100].decode('utf-8', errors='ignore')
        print(f"  {p} first 100 bytes: {start}")
        if '{' in start:
            # Try to find the last '}'
            last_bracket = r.rfind(b'}')
            if last_bracket != -1:
                json_data = r[:last_bracket+1].decode('utf-8')
                return json.loads(json_data)
    except Exception as e:
        print(f"  {p}: Plain JSON failed: {e}")

    # 2. Try offset 4 (STS/Fog)
    try:
        decompressed = zlib.decompress(r[4:])
        print(f"  {p} decompressed sample (hex): {decompressed[:64].hex()}")
        print(f"  {p} decompressed sample (text): {decompressed[:128].decode('utf-8', errors='ignore')}")
        # Try to find JSON inside decompressed
        start_bracket = decompressed.find(b'{')
        if start_bracket != -1:
            last_bracket = decompressed.rfind(b'}')
            if last_bracket != -1:
                return json.loads(decompressed[start_bracket:last_bracket+1].decode('utf-8'))
    except Exception as e:
        print(f"  {p}: ZLIB failed: {e}")

    return None

def analyze_folder(folder):
    res = {}
    files = os.listdir(folder)
    
    targets = [
        ("Player", "CompleteSave.cfg"),
        ("STS", "sts_level_us_01_01.cfg"),
    ]
    
    for key, filename in targets:
        path = os.path.join(folder, filename)
        if os.path.exists(path):
            data = d(path)
            if data:
                res[key] = "SUCCESS"
                if key == "Player":
                    ssl = data.get("CompleteSave", {}).get("SslValue", {})
                    res["Player_Data"] = list(ssl.keys())[:5]
                else:
                    res["STS_Keys"] = list(data.keys())[:5] if isinstance(data, dict) else "NOT_DICT"

    return res

if __name__ == "__main__":
    TARGET = r"e:\Snow Runner New Tool\remote2\remote"
    print("\nREPORT:")
    print(json.dumps(analyze_folder(TARGET), indent=2))
