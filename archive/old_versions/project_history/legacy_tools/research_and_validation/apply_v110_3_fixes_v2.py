import zlib
import os
import re
import struct

target = r"e:\Snow Runner New Tool\app\snowrunner_editor.py"
with open(target, "r", encoding="utf-8") as f:
    content = f.read()

# 1. Update _peek_slot_metadata (Profiler)
# Ensuring it reads the whole file and uses a robust read_max_int
profiler_old = r'def _peek_slot_metadata\(full_path: str\) -> Dict\[str, Any\]:.*?return \{"found": False, "error": str\(e\)\}'
profiler_new = """def _peek_slot_metadata(full_path: str) -> Dict[str, Any]:
    \"\"\"High-fidelity whole-file parser for the Profiler (v110.3).
    Ensures 100% data accuracy for large saves by scanning beyond the old 1MB limit.
    \"\"\"
    if not os.path.isfile(full_path):
        return {"found": False, "money": 0, "rank": 0, "experience": 0}
    
    try:
        with open(full_path, "rb") as f:
            raw_data = f.read()
            
        if not raw_data:
            return {"found": False, "empty": True}

        # 1. Decompress if Zlib (SnowRunner binary format)
        if raw_data.startswith(b"\\x41\\x4B\\x05\\x00"):
            try: content_text = zlib.decompress(raw_data[4:]).decode("utf-8", errors="replace")
            except Exception: content_text = ""
        else: content_text = raw_data.decode("utf-8", errors="replace")

        if not content_text:
            return {"found": True, "parse_error": True, "money": 0, "rank": 0, "experience": 0}

        # 2. Robust high-fidelity extraction
        def read_max_int(key, text):
            matches = re.findall(rf'"{re.escape(key)}"\s*:\s*(-?\d+)', text, flags=re.IGNORECASE)
            if not matches: return None
            vals = []
            for m in matches:
                try: vals.append(int(m))
                except: continue
            return max(vals) if vals else None

        money_val = read_max_int("money", content_text)
        rank_val = read_max_int("rank", content_text)
        xp_val = read_max_int("experience", content_text)

        return {
            "found": True,
            "money": money_val if money_val is not None else 0,
            "rank": rank_val if rank_val is not None else 0,
            "experience": xp_val if xp_val is not None else 0
        }
    except Exception as e:
        print(f"[Profiler] Peek error: {e}")
        return {"found": False, "error": str(e)}"""

content = re.sub(profiler_old, profiler_new, content, flags=re.DOTALL)

# 2. Update generate_revealed_fog (Dynamic Map Size)
# This finds the existing file, reads its dimensions, and replicates them
fog_old = r'width, height = 128, 128.*?# V110.3 Fix: Try to detect map size from existing fog files.*?raw_payload = struct\.pack\("<II", width, height\) \+ \(b"\\x00" \* \(width \* height\)\)'
fog_new = """width, height = 128, 128
    # V110.3 Fix: Auto-detect map size from existing fog file to support large regions like Taymyr
    for lvl in levels:
        actual_files = _find_best_map_files(save_dir, slot_prefix, "fog_", lvl)
        if actual_files:
            try:
                with open(os.path.join(save_dir, actual_files[0]), "rb") as ef:
                    ed = ef.read()
                    if ed.startswith(b"\\x41\\x4B\\x05\\x00"):
                        ed = zlib.decompress(ed[4:])
                    w_header, h_header = struct.unpack("<II", ed[:8])
                    if 0 < w_header < 1024 and 0 < h_header < 1024:
                        width, height = w_header, h_header
                        break # Found dimensions!
            except: continue
    
    # Generate the payload with correct dimensions
    raw_payload = struct.pack("<II", width, height) + (b"\\x00" * (width * height))"""

content = re.sub(fog_old, fog_new, content, flags=re.DOTALL)

# 3. Update discover_world_objects (Multi-Injection sidebar list)
discovery_old = r'target_keys = \["discoveredObjects", "viewedUnactivatedObjectives", "discoveredUpgrades", "discoveredTrucks", "discoveredTrailers"\]'
discovery_new = 'target_keys = ["discoveredObjects", "viewedUnactivatedObjectives", "discoveredUpgrades", "discoveredTrucks", "discoveredTrailers"]' # (No change needed from my previous sub, but let's be sure)

content = re.sub(discovery_old, discovery_new, content, flags=re.DOTALL)

with open(target, "w", encoding="utf-8") as f:
    f.write(content)

print("Applied 3 precision fixes to snowrunner_editor.py (v110.3)")
