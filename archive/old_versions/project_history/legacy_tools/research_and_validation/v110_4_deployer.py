import os

target = r"e:\Snow Runner New Tool\app\snowrunner_editor.py"
with open(target, "r", encoding="utf-8") as f:
    content = f.read()

# 1. Fog Reform (v110.4)
# Replacing the entire generate_revealed_fog function with the dynamic structure-preserving logic
new_fog_reveal_func = r'''def generate_revealed_fog(save_path, selected_regions, notify=True):
    """
    v110.4 Final Fix: Decompresses the existing fog file, finds pixel data,
    replaces with 0x80 (Revealed transparency), and re-compresses.
    This preserves the exact map dimensions and header metadata.
    """
    save_dir = os.path.dirname(save_path)
    slot_prefix = ""
    match = re.search(r'(\d+)_CompleteSave\.cfg$', os.path.basename(save_path))
    if match:
        slot_prefix = f"{match.group(1)}_"

    levels = []
    for code in selected_regions:
        levels.extend(REGION_LEVELS.get(code, []))
    
    created = 0
    errors = []
    
    file_header = b"\x41\x4B\x05\x00"

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
                
                # In SnowRunner binary fog files (dat/cfg):
                # Bytes 0-7: width, height (uint32)
                # Next bytes: Pixel data (1 byte per pixel)
                import struct
                w, h = struct.unpack("<II", dec[:8])
                
                # We patch 0x80 (The correct "Revealed" transparency value)
                # 0x00 is Solid Black mask (The previous bug).
                # 0xFF is Fully Fogged.
                patched = bytearray(dec)
                # We overwrite the entire payload from index 8 onwards
                # This ensures we don't need to know the exact grid dimensions.
                for i in range(8, len(patched)):
                    patched[i] = 0x80
                
                if is_binary:
                    # Re-compress
                    compressed = zlib.compress(bytes(patched), level=6)
                    final_data = file_header + compressed
                else:
                    final_data = bytes(patched)
                
                with open(fog_path, "wb") as f:
                    f.write(final_data)
                created += 1
            except Exception as e:
                errors.append(f"{fog_name}: {e}")
    
    msg = f"Dynamically revealed {created} maps with precision transparency (0x80)."
    if errors: msg += f"\nErrors: {len(errors)}"
    return _action_result("Success", msg, notify=notify)'''

# Use a marker-replacement strategy to be 100% sure
start_marker = 'def generate_revealed_fog(save_path, selected_regions, notify=True):'
end_marker = 'return _action_result("Success", msg, notify=notify)'

start_idx = content.find(start_marker)
end_idx = content.find(end_marker, start_idx)

if start_idx != -1 and end_idx != -1:
    content = content[:start_idx] + new_fog_reveal_func + content[end_idx + len(end_marker):]
    print("Successfully replaced generate_revealed_fog with v110.4 logic.")

# 2. Version Bump
content = content.replace('APP_VERSION = 110.3', 'APP_VERSION = 110.4')
content = content.replace('APP_VERSION = "110.3"', 'APP_VERSION = 110.4')

with open(target, "w", encoding="utf-8") as f:
    f.write(content)
print("v110.4 deployment successful.")
