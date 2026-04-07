import os
import zlib
import re
import json

def analyze_save(path):
    print(f"Analyzing Save: {path}")
    if not os.path.exists(path):
        print("File not found.")
        return

    with open(path, "rb") as f:
        data = f.read()
    
    print(f"Header (Hex): {data[:16].hex(' ')}")
    
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

    # Keys to find
    keys = [
        "money", "level", "experience",
        "discoveredTrucks", "discoveredUpgrades", "discoveredTrailers",
        "discoveredWatchtowers", "discoveredMissions"
    ]
    for key in keys:
        match = re.search(rf'\"{key}\"\s*:\s*(\[.*?\]|\d+|true|false)', content, re.DOTALL)
        if match:
            raw = match.group(0)
            # Truncate if it's a long list
            if len(raw) > 100:
                print(f"{key}: {raw[:100]}...]")
            else:
                print(f"{key}: {raw}")
        else:
            print(f"{key}: NOT FOUND.")

def analyze_fog(path):
    print(f"\nAnalyzing Fog File: {path}")
    if not os.path.exists(path):
        print("File not found.")
        return

    with open(path, "rb") as f:
        data = f.read()
    print(f"Size: {len(data)} bytes")
    print(f"Header: {data[:16].hex(' ')}")
    if data.startswith(b'AK\x05\x00'):
        print("Fog is COMPRESSED.")
        try:
            dec = zlib.decompress(data[4:])
            print(f"Decompressed Size: {len(dec)} bytes")
            print(f"Decompressed (Hex): {dec[:32].hex(' ')}")
        except Exception as e:
            print(f"Fog decompression failed: {e}")

if __name__ == "__main__":
    analyze_save(r"e:\Snow Runner New Tool\remote\CompleteSave.cfg")
    analyze_fog(r"e:\Snow Runner New Tool\remote\fog_level_ru_02_01.dat")
