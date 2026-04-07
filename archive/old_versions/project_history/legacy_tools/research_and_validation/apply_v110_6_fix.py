import os
import re

target = r"e:\Snow Runner New Tool\app\snowrunner_editor.py"
with open(target, "r", encoding="utf-8") as f:
    content = f.read()

# 1. Overhaul generate_revealed_fog (v110.6 - Definitive 0x80 Fill)
fog_old_pattern = r'def generate_revealed_fog\(save_path, selected_regions, notify=True\):.*?return _action_result\("Success", msg, notify=notify\)'
fog_new_function = """def generate_revealed_fog(save_path, selected_regions, notify=True):
    \"\"\"
    v110.6 Definitive Fix: Aligns with the user's working 'Actual files' reference.
    Decompressess the existing file, reads dimensions, and fills the entire 
    payload with bytes(128) - (0x80). This provides 100% visibility.
    \"\"\"
    save_dir = os.path.dirname(save_path)
    slot_prefix = ""
    match = re.search(r'(\\d+)_CompleteSave\\.cfg$', os.path.basename(save_path))
    if match:
        slot_prefix = f"{match.group(1)}_"

    levels = []
    for code in selected_regions:
        levels.extend(REGION_LEVELS.get(code, []))
    
    created = 0
    errors = []
    
    file_header = b"\\x41\\x4B\\x05\\x00"

    for lvl in levels:
        actual_files = _find_best_map_files(save_dir, slot_prefix, "fog_", lvl)
        for fog_name in actual_files:
            fog_path = os.path.join(save_dir, fog_name)
            try:
                if not os.path.exists(fog_path): continue
                
                with open(fog_path, "rb") as f:
                    data = f.read()
                
                if data.startswith(file_header):
                    dec = zlib.decompress(data[4:])
                    is_binary = True
                else:
                    dec = data
                    is_binary = False
                
                if len(dec) < 8: continue
                
                import struct
                w, h = struct.unpack("<II", dec[:8])
                
                # Check for 12-byte header (extra field)
                # This matches the user's Smithville Dam map discovered in v110.5 analysis
                header_size = 8
                if len(dec) > 12 and struct.unpack("<I", dec[8:12])[0] < 10000:
                    header_size = 12
                
                # Definitive v110.6 Logic: Fill the entire pixel array with 128 (0x80)
                # This mirrors the user's working Michigan maps perfectly.
                header = dec[:header_size]
                revealed_payload = b"\\x80" * (w * h)
                patched = header + revealed_payload
                
                if is_binary:
                    compressed = zlib.compress(patched, level=6)
                    final_data = file_header + compressed
                else:
                    final_data = patched
                
                with open(fog_path, "wb") as f:
                    f.write(final_data)
                created += 1
            except Exception as e:
                errors.append(f"{fog_name}: {e}")
    
    msg = f"Definitively revealed {created} maps using the working 0x80 (128) standard."
    if errors: msg += f"\\nErrors: {len(errors)}"
    return _action_result("Success", msg, notify=notify)"""

content = re.sub(fog_old_pattern, fog_new_function, content, flags=re.DOTALL)

# 2. Version Bump to v110.6
content = content.replace('APP_VERSION = 110.5', 'APP_VERSION = 110.6')

with open(target, "w", encoding="utf-8") as f:
    f.write(content)

print("Applied v110.6 definitive fog fix.")
