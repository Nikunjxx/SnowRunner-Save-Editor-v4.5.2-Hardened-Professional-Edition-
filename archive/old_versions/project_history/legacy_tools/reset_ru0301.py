import os, zlib, struct

def reset_lake_kovd(filepath, reveal=True):
    print(f"[{'HEAL' if reveal else 'RESET'}] Processing: {filepath}")
    
    if not os.path.exists(filepath):
        print(f"Error: File not found: {filepath}")
        return
        
    try:
        with open(filepath, "rb") as f:
            data = f.read()
            
        # 1. Decompress
        if not data.startswith(b"\x41\x4B\x05\x00"):
            print("Error: Not a standard SnowRunner binary file.")
            return
            
        dec = zlib.decompress(data[4:])
        
        # 2. Reconstruct Header (Standard 589x589 for Lake Kovd)
        w, h = 589, 589
        header = struct.pack("<II", w, h)
        
        # 3. Wipe Payload
        # 0x80 (128) is 'Revealed', 0x00 is 'Hidden'
        pixel_val = 0x80 if reveal else 0x00
        new_payload = bytes([pixel_val]) * (w * h)
        
        # 4. Mandatory Season 1 Footer (16 bytes)
        # We try to capture it from the original file if possible, 
        # otherwise use a standard healthy footer for Kola Peninsula.
        original_footer = dec[8 + w*h:] if len(dec) >= (8 + w*h) else b""
        if len(original_footer) != 16:
            # Standard DLC footer for RU_03_01
            footer = b"\x00\x00\x00\x00\x00\x00\x00\x00\x02\x00\x00\x00\x00\x00\x00\x00"
            print("Warning: Original footer invalid. Injecting standard DLC footer.")
        else:
            footer = original_footer
            print("Success: Preserved original map metadata.")

        # 5. Reassemble & Compress
        final_dec = header + new_payload + footer
        print(f"Final uncompressed size: {len(final_dec)} bytes (Target: 346945)")
        
        compressed = zlib.compress(final_dec, level=6)
        final_data = b"\x41\x4B\x05\x00" + compressed
        
        # 6. Save back
        with open(filepath, "wb") as f:
            f.write(final_data)
            
        print("Done! File has been healed and reset to Revealed state.")
        
    except Exception as e:
        print(f"Critical Error during reset: {e}")

# Run on the file in the root directory (as specified by user)
target = r"e:\Snow Runner New Tool\fog_level_ru_03_01.cfg"
# Also try the one in research_and_validation/remote/ if root is missing
if not os.path.exists(target):
    target = r"e:\Snow Runner New Tool\research_and_validation\remote\fog_level_ru_03_01.cfg"

reset_lake_kovd(target, reveal=True)
