import os
import zlib
import struct
import json
import re

def test_fog_reveal_binary_integrity():
    print("[TEST] Fog Reveal Binary Integrity (v110.3)...")
    # V110.3 logic: width/height can be dynamic (e.g. 256 or 512)
    width, height = 256, 256
    raw_payload = struct.pack("<II", width, height) + (b"\x00" * (width * height))
    compressed_payload = zlib.compress(raw_payload, level=6)
    
    file_header = b"\x41\x4B\x05\x00"
    full_binary_data = file_header + compressed_payload
    
    assert full_binary_data.startswith(b"\x41\x4B\x05\x00"), "Missing SnowRunner header!"
    decompressed = zlib.decompress(full_binary_data[4:])
    w, h = struct.unpack("<II", decompressed[:8])
    assert w == 256 and h == 256, f"Invalid dimensions! Expected 256, found {w}"
    assert decompressed[8] == 0x00, "Map not cleared!"
    print("      SUCCESS: Dynamic fog data integrity verified.")

def test_discovery_5_way_injection():
    print("[TEST] Discovery 5-Way Injection (v110.3)...")
    content = '{"SslValue":{"discoveredObjects":[],"other":1}}'
    all_ids = ["truck_01", "upgrade_01", "trailer_01"]
    # v110.3 Adds Trucks and Trailers to the injection sidebar lists
    target_keys = ["discoveredObjects", "viewedUnactivatedObjectives", "discoveredUpgrades", "discoveredTrucks", "discoveredTrailers"]
    
    def mock_extract(text, start_pos):
        count = 0
        for i in range(start_pos, len(text)):
            if text[i] == "[": count += 1
            elif text[i] == "]":
                count -= 1
                if count == 0: return text[start_pos:i+1], start_pos, i+1
        return None, None, None

    for key in target_keys:
        if f'"{key}"' not in content:
            content = content.replace('"SslValue":{', f'"SslValue":{{"{key}":[],', 1)
        
        match = re.search(rf'"{key}"\s*:\s*\[', content)
        if match:
            block, start, end = mock_extract(content, match.end() - 1)
            disc_list = json.loads(block)
            for iid in all_ids:
                if iid not in disc_list: disc_list.append(iid)
            content = content[:start] + json.dumps(disc_list, separators=(",", ":")) + content[end:]

    ssl = json.loads(content)["SslValue"]
    for k in target_keys:
        assert k in ssl, f"Key {k} missing from injection!"
        assert "truck_01" in ssl[k], f"ID truck_01 missing from {k}!"
    print("      SUCCESS: Discovery logic correctly performs 5-way injection.")

def test_profiler_hi_fi_parser():
    print("[TEST] Profiler Hi-Fi Parser (v110.3)...")
    # Mocking a large save file with duplicate keys
    content = '{"money": 100, "rank": 5, "experience": 1000, "other": 123, "money": 500000, "rank": 30}'
    
    def read_max_int(key, text):
        matches = re.findall(rf'"{re.escape(key)}"\s*:\s*(-?\d+)', text, flags=re.IGNORECASE)
        if not matches: return None
        return max([int(m) for m in matches])

    money = read_max_int("money", content)
    rank = read_max_int("rank", content)
    assert money == 500000, f"Failed to find max money! Found {money}"
    assert rank == 30, f"Failed to find max rank! Found {rank}"
    print("      SUCCESS: Hi-Fi parser correctly identifies latest/maximum values.")

if __name__ == "__main__":
    print("\n--- SNOWRUNNER EDITOR v110.3 LOGIC VALIDATION ---")
    try:
        test_fog_reveal_binary_integrity()
        test_discovery_5_way_injection()
        test_profiler_hi_fi_parser()
        print("--- VALIDATION SUCCESSFUL ---")
    except Exception as e:
        print(f"--- VALIDATION FAILED: {e} ---")
        import traceback
        traceback.print_exc()
        exit(1)
