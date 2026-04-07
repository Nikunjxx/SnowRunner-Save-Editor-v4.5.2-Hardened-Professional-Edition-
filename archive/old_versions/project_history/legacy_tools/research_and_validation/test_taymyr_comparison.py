import os
import zlib
import struct
from collections import Counter

def analyze(p):
    if not os.path.exists(p): return f"{os.path.basename(p)}: File not found."
    with open(p, 'rb') as f:
        d = f.read()
    if d.startswith(b'\x41\x4B\x05\x00'):
        dec = zlib.decompress(d[4:])
    else:
        dec = d
    
    if len(dec) < 8: return f"{os.path.basename(p)}: Too small."
    
    w, h = struct.unpack('<II', dec[:8])
    # Detect header size (as per v110.6 logic)
    header_size = 8
    if len(dec) > 12 and struct.unpack("<I", dec[8:12])[0] < 10000:
        header_size = 12
        
    counts = Counter(dec[header_size:])
    top = counts.most_common(2)
    return {
        "name": os.path.basename(p),
        "header": f"{w}x{h}",
        "header_size": header_size,
        "total_size": len(dec),
        "pixels": len(dec[header_size:]),
        "top_values": top
    }

# 1. REFERENCE (Actual files)
ref = analyze(r'e:\Snow Runner New Tool\Actual files\fog_level_us_01_01.dat')

# 2. TAYMYR BEFORE (Remote)
tay_before = analyze(r'e:\Snow Runner New Tool\remote\fog_level_ru_02_01.dat')

print("--- REFERENCE (Actual files/Working Map) ---")
print(ref)
print("\n--- TAYMYR BEFORE (Remote/Failing Map) ---")
print(tay_before)

# 3. RUN v110.6 LOGIC (Simulation inside script)
header = zlib.decompress(open(r'e:\Snow Runner New Tool\remote\fog_level_ru_02_01.dat', 'rb').read()[4:])[:tay_before['header_size']]
new_payload = b'\x80' * tay_before['pixels']
final_dec = header + new_payload
# (Simulate compression skip for analysis)

print("\n--- TAYMYR AFTER (v110.6 Simulated Patch) ---")
c_after = Counter(final_dec[tay_before['header_size']:])
print({
    "name": "fog_level_ru_02_01.dat (Patched)",
    "header": tay_before['header'],
    "pixels": len(new_payload),
    "top_values": c_after.most_common(1)
})
