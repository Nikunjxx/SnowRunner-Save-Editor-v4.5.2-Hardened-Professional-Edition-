import os
import re

target = r"e:\Snow Runner New Tool\app\snowrunner_editor.py"
with open(target, "r", encoding="utf-8") as f:
    content = f.read()

# 1. Overhaul generate_revealed_fog (v110.5 - Precision Patching)
fog_old_pattern = r'def generate_revealed_fog\(save_path, selected_regions, notify=True\):.*?return _action_result\("Success", msg, notify=notify\)'
fog_new_function = """def generate_revealed_fog(save_path, selected_regions, notify=True):
    \"\"\"
    v110.5 Final Fix: Decompresses the existing fog file, identifies the pixel data 
    start by checking the header, patches only Fog (0xFF) to revealed (0x00) 
    while preserving every other bite (e.g. 0x80 or header metadata).
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
                
                # Detect the header offset: 
                # (w*h) pixels are at the end. The rest is header.
                header_size = len(dec) - (w * h)
                if header_size < 8 or header_size > 1024:
                    # Fallback if size calculation is weird
                    header_size = 8
                    if len(dec) > 12 and struct.unpack("<I", dec[8:12])[0] < 10000:
                        header_size = 12
                
                patched = bytearray(dec)
                # Selective Patching: Only convert Fog (0xFF) to Revealed (0x00)
                # This leaves existing 0x80 or custom map data untouched.
                for i in range(header_size, len(patched)):
                    if patched[i] == 0xFF:
                        patched[i] = 0x00
                
                if is_binary:
                    compressed = zlib.compress(bytes(patched), level=6)
                    final_data = file_header + compressed
                else:
                    final_data = bytes(patched)
                
                with open(fog_path, "wb") as f:
                    f.write(final_data)
                created += 1
            except Exception as e:
                errors.append(f"{fog_name}: {e}")
    
    msg = f"Precisely patched {created} fog files with header preservation."
    if errors: msg += f"\\nErrors: {len(errors)}"
    return _action_result("Success", msg, notify=notify)"""

content = re.sub(fog_old_pattern, fog_new_function, content, flags=re.DOTALL)

# 2. Version Bump to v110.5
content = content.replace('APP_VERSION = 110.4', 'APP_VERSION = 110.5')

with open(target, "w", encoding="utf-8") as f:
    f.write(content)

print("Applied v110.5 precision fog fix.")
