import os

target = r"e:\Snow Runner New Tool\app\snowrunner_editor.py"
with open(target, "r", encoding="utf-8") as f:
    content = f.read()

# 1. Profiler Fix (Whole-file scan)
old_profiler_block = """        with open(full_path, "rb") as f:
            raw_data = f.read(1024 * 1024) # Read 1MB max for the peek"""
new_profiler_block = """        with open(full_path, "rb") as f:
            raw_data = f.read() # Read whole file for v110.3 high-fidelity scan"""

if old_profiler_block in content:
    content = content.replace(old_profiler_block, new_profiler_block)
    print("Fixed Profiler File Buffer (Whole-file scan).")

# 2. Profiler Logic Upgrade (Read Max Int)
old_profiler_logic = """        def find_val(key):
            # Look for "key":123 or "key": 123
            m = re.search(fr'"{key}"\s*:\s*(\d+)', content, re.IGNORECASE)
            return int(m.group(1)) if m else 0

        return {
            "found": True,
            "money": find_val("money"),
            "rank": find_val("rank"),
            "experience": find_val("experience")
        }"""
new_profiler_logic = """        def read_max_int(key, text):
            # Scan entire decompressed content for ALL occurrences (v110.3)
            matches = re.findall(rf'"{re.escape(key)}"\s*:\s*(-?\d+)', text, flags=re.IGNORECASE)
            if not matches: return None
            vals = []
            for m in matches:
                try: vals.append(int(m))
                except: continue
            return max(vals) if vals else None

        money_val = read_max_int("money", content)
        rank_val = read_max_int("rank", content)
        xp_val = read_max_int("experience", content)

        return {
            "found": True,
            "money": money_val if money_val is not None else 0,
            "rank": rank_val if rank_val is not None else 0,
            "experience": xp_val if xp_val is not None else 0
        }"""
if old_profiler_logic in content:
    content = content.replace(old_profiler_logic, new_profiler_logic)
    print("Fixed Profiler Logic (Max-Int High Fidelity).")

# 3. Fog Reveal Fix (Dynamic Size Detection)
old_fog_block = """    width, height = 128, 128
    # Clear map value is 0x00, not 0xFF (foggy)
    raw_payload = struct.pack("<II", width, height) + (b"\\x00" * (width * height))"""
new_fog_block = """    width, height = 128, 128
    # V110.3 Fix: Detect map size from existing fog file (supports Taymyr/Amur larger maps)
    for lvl in levels:
        actual_files = _find_best_map_files(save_dir, slot_prefix, "fog_", lvl)
        if actual_files:
            try:
                with open(os.path.join(save_dir, actual_files[0]), "rb") as ef:
                    ed = ef.read()
                    if ed.startswith(b"\\x41\\x4B\\x05\\x00"):
                        import zlib
                        ed = zlib.decompress(ed[4:])
                    import struct
                    e_w, e_h = struct.unpack("<II", ed[:8])
                    if 0 < e_w < 1024 and 0 < e_h < 1024:
                        width, height = e_w, e_h
                        break
            except: continue
    
    import struct
    # Clear map value is 0x00, not 0xFF (foggy)
    raw_payload = struct.pack("<II", width, height) + (b"\\x00" * (width * height))"""

if old_fog_block in content:
    content = content.replace(old_fog_block, new_fog_block)
    print("Fixed Fog Reveal (Dynamic Size).")

# 4. Discovery Expansion
old_disc_keys = 'target_keys = ["discoveredObjects", "viewedUnactivatedObjectives", "discoveredUpgrades"]'
new_disc_keys = 'target_keys = ["discoveredObjects", "viewedUnactivatedObjectives", "discoveredUpgrades", "discoveredTrucks", "discoveredTrailers"]'

if old_disc_keys in content:
    content = content.replace(old_disc_keys, new_disc_keys)
    print("Fixed Discovery Expansion (Trucks/Trailers).")

# 5. Version Bump
content = content.replace('APP_VERSION = "110.2"', 'APP_VERSION = "110.3"')

with open(target, "w", encoding="utf-8") as f:
    f.write(content)
print("v110.3 deployment complete.")
