import os
import zlib
import re

def analyze_save(path):
    print(f"Analyzing {path}...")
    if not os.path.exists(path):
        print("File not found.")
        return

    with open(path, "rb") as f:
        header = f.read(16)
        print(f"Header (Hex): {header.hex(' ')}")
        
        f.seek(0)
        data = f.read()

    # Check for Zlib header AK\x05\x00
    if data.startswith(b'AK\x05\x00'):
        print("Detected Zlib compression.")
        try:
            content = zlib.decompress(data[4:]).decode('utf-8', errors='ignore')
            print("Successfully decompressed.")
        except Exception as e:
            print(f"Decompression failed: {e}")
            return
    else:
        print("Plain text or unknown format.")
        content = data.decode('utf-8', errors='ignore')

    # Discovery analysis
    discoveries = [
        "discoveredTrucks",
        "discoveredUpgrades",
        "discoveredTrailers",
        "discoveredWatchtowers"
    ]
    for key in discoveries:
        match = re.search(rf'"{key}"\s*:\s*\[(.*?)\]', content, re.DOTALL)
        if match:
            items = match.group(1).split(",")
            print(f"{key}: {len(items)} items found.")
        else:
            print(f"{key}: NOT FOUND.")

    # Money/Rank check
    for key in ["money", "level", "experience"]:
        match = re.search(rf'"{key}"\s*:\s*(\d+)', content)
        if match:
            print(f"{key}: {match.group(1)}")
        else:
            print(f"{key}: MISSING.")

if __name__ == "__main__":
    analyze_save("e:/Snow Runner New Tool/remote/CompleteSave.cfg")
    print("-" * 20)
    # Analyze a fog file
    fog_path = "e:/Snow Runner New Tool/remote/fog_level_ru_02_01.dat"
    if os.path.exists(fog_path):
        with open(fog_path, "rb") as f:
            data = f.read()
            print(f"Fog file {os.path.basename(fog_path)} size: {len(data)} bytes")
            print(f"Fog content (Hex): {data.hex(' ')}")
