import os
import re

target = r"e:\Snow Runner New Tool\app\snowrunner_editor.py"
with open(target, "r", encoding="utf-8") as f:
    content = f.read()

# 1. Overhaul generate_revealed_fog (Dynamic Patching 0x80)
# We replace the entire function to ensure clean logic
fog_old_pattern = r'def generate_revealed_fog\(save_path, selected_regions, notify=True\):.*?return _action_result\("Success", msg, notify=notify\)'
fog_new_function = """def generate_revealed_fog(save_path, selected_regions, notify=True):
    \"\"\"
    v110.4 Emergency Fix: Decompresses existing fog files, patches them with the correct 
    revealed value (0x80), and re-compresses. This preserves exact map dimensions (e.g. 589x589).
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
    
    # Correct SnowRunner Header: 41 4B 05 00
    file_header = b"\\x41\\x4B\\x05\\x00"

    for lvl in levels:
        actual_files = _find_best_map_files(save_dir, slot_prefix, "fog_", lvl)
        for fog_name in actual_files:
            fog_path = os.path.join(save_dir, fog_name)
            try:
                # 1. Read existing file structure
                with open(fog_path, "rb") as f:
                    data = f.read()
                
                # 2. Decompress
                if data.startswith(file_header):
                    dec = zlib.decompress(data[4:])
                else:
                    dec = data # Plain binary
                
                if len(dec) < 8: continue
                
                # 3. Patch Pixel Data
                # SnowRunner: 0xFF=Fog, 0x80=Revealed, 0x00=BlackMask
                # We overwrite everything after the 8-byte header (dimensions)
                import struct
                w, h = struct.unpack("<II", dec[:8])
                # We use a bytearray for efficient patching
                patched = bytearray(dec)
                # Ensure we don't exceed buffer if header is longer (e.g. 12 or 16 bytes)
                # But typically it's 8 or 12. Most reliable is to keep the header as-is.
                pixel_start = 8
                # Check for 12-byte header (extra field)
                if len(dec) > 12 and struct.unpack("<I", dec[8:12])[0] < 10000:
                    pixel_start = 12 if len(dec) > (w*h + 8) else 8
                
                # SnowRunner usually starts pixels after the dimensions (8 bytes)
                # We fill with 0x80 (transparency)
                for i in range(8, len(patched)):
                    patched[i] = 0x80
                
                # 4. Re-Compress
                compressed_payload = zlib.compress(bytes(patched), level=6)
                full_binary_data = file_header + compressed_payload
                
                with open(fog_path, "wb") as f:
                    f.write(full_binary_data)
                created += 1
            except Exception as e:
                errors.append(f"{fog_name}: {e}")
    
    msg = f"Dynamically patched {created} fog files with 'Revealed' transparency (0x80)."
    if errors:
        msg += f"\\nErrors: {len(errors)}"
    return _action_result("Success", msg, notify=notify)"""

content = re.sub(fog_old_pattern, fog_new_function, content, flags=re.DOTALL)

# 2. Version Bump to v110.4
content = content.replace('APP_VERSION = 110.3', 'APP_VERSION = 110.4')

with open(target, "w", encoding="utf-8") as f:
    f.write(content)

print("Applied v110.4 emergency fog fix.")
