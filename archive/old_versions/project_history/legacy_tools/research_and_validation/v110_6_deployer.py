import os

target = r"e:\Snow Runner New Tool\app\snowrunner_editor.py"
with open(target, "r", encoding="utf-8") as f:
    content = f.read()

# 1. Fog Reveal Definitive (v110.6)
# Replacing the entire generate_revealed_fog function with the full-fill 128 logic
new_fog_reveal_func = r'''def generate_revealed_fog(save_path, selected_regions, notify=True):
    """
    v110.6 Definitive Fix: Aligns with the user's working 'Actual files' reference.
    Decompressess the existing file, reads dimensions, and fills the entire 
    payload with 128 (0x80). This provides 100% binary-perfect visibility.
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
                
                import struct
                w, h = struct.unpack("<II", dec[:8])
                
                # Check for 12-byte header (extra field)
                header_size = 8
                if len(dec) > 12 and struct.unpack("<I", dec[8:12])[0] < 10000:
                    header_size = 12
                
                # Full Reveal v110.6 Logic: Perfect fill of 128 (0x80)
                header = dec[:header_size]
                revealed_payload = b"\x80" * (w * h)
                final_dec = header + revealed_payload
                
                if is_binary:
                    compressed = zlib.compress(final_dec, level=6)
                    final_data = file_header + compressed
                else:
                    final_data = final_dec
                
                with open(fog_path, "wb") as f:
                    f.write(final_data)
                created += 1
            except Exception as e:
                errors.append(f"{fog_name}: {e}")
    
    msg = f"Definitively revealed {created} maps using the 128 (0x80) standard."
    if errors: msg += f"\nErrors: {len(errors)}"
    return _action_result("Success", msg, notify=notify)'''

# Marker-based replacement for 100% robustness
start_marker = 'def generate_revealed_fog(save_path, selected_regions, notify=True):'
end_marker = 'return _action_result("Success", msg, notify=notify)'

start_idx = content.find(start_marker)
end_idx = content.find(end_marker, start_idx)

if start_idx != -1 and end_idx != -1:
    content = content[:start_idx] + new_fog_reveal_func + content[end_idx + len(end_marker):]
    print("Injected v110.6 fog logic.")

# 2. Version Bump
content = content.replace('APP_VERSION = 110.5', 'APP_VERSION = 110.6')

with open(target, "w", encoding="utf-8") as f:
    f.write(content)
print("v110.6 deployment successfully patched.")
