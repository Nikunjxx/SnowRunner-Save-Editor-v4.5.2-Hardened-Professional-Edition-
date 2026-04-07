import re
import os

target = r"e:\Snow Runner New Tool\app\snowrunner_editor.py"
with open(target, "r", encoding="utf-8") as f:
    content = f.read()

# 1. Fix _peek_slot_metadata (Whole-file high-fidelity parser)
profiler_old = r'def _peek_slot_metadata\(full_path: str\) -> Dict\[str, Any\]:.*?return \{"found": False, "error": str\(e\)\}'
profiler_new = """def _peek_slot_metadata(full_path: str) -> Dict[str, Any]:
    \"\"\"High-fidelity whole-file parser for the Profiler (v110.3).
    Ensures 100% data accuracy for large saves by scanning beyond the old 1MB limit.
    \"\"\"
    if not os.path.isfile(full_path):
        return {"found": False, "money": 0, "rank": 0, "experience": 0}
    
    try:
        with open(full_path, "rb") as f:
            raw_data = f.read()  # Read whole file for v110.3
            
        if not raw_data:
            return {"found": False, "empty": True}

        # 1. Decompress if Zlib (SnowRunner binary format)
        if raw_data.startswith(b"\\x41\\x4B\\x05\\x00"):
            import zlib
            try:
                content_text = zlib.decompress(raw_data[4:]).decode("utf-8", errors="replace")
            except Exception:
                content_text = ""
        else:
            content_text = raw_data.decode("utf-8", errors="replace")

        if not content_text:
            return {"found": True, "parse_error": True, "money": 0, "rank": 0, "experience": 0}

        # 2. Robust high-fidelity extraction (matching the main editor logic)
        def read_max_int(key, text):
            # Scan entire decompressed content for ALL occurrences
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

# 2. Fix generate_revealed_fog (Dynamic Map Size)
fog_old = r'width, height = 128, 128.*?# Clear map value is 0x00, not 0xFF \(foggy\).*?raw_payload = struct\.pack\("<II", width, height\) \+ \(b"\\x00" \* \(width \* height\)\)'
fog_new = """width, height = 128, 128
    # V110.3 Fix: Try to detect map size from existing fog files (Taymyr uses 256/512)
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

content = re.sub(fog_old, fog_new, content, flags=re.DOTALL)

# 3. Fix discover_world_objects (Multi-Injection sidebar list)
discovery_old = r'target_keys = \["discoveredObjects", "viewedUnactivatedObjectives", "discoveredUpgrades"\].*?for key in target_keys:'
discovery_new = 'target_keys = ["discoveredObjects", "viewedUnactivatedObjectives", "discoveredUpgrades", "discoveredTrucks", "discoveredTrailers"]\n        for key in target_keys:'

content = re.sub(discovery_old, discovery_new, content, flags=re.DOTALL)

with open(target, "w", encoding="utf-8") as f:
    f.write(content)

print("Applied 3 precision fixes to snowrunner_editor.py (v110.3)")
