import zlib
import struct
from collections import Counter

f_path = r"e:\Snow Runner New Tool\remote\fog_level_us_01_01.dat"
print(f"Analyzing {f_path}...")
with open(f_path, "rb") as f:
    data = f.read()

if data.startswith(b'AK\x05\x00'):
    print("Detected Zlib Header (AK\\x05\\x00)")
    dec = zlib.decompress(data[4:])
    print(f"Decompressed Size: {len(dec)} bytes")
    
    # Unpack Header
    w, h = struct.unpack("<II", dec[:8])
    print(f"Dimensions: {w}x{h}")
    
    # Frequency analysis
    payload = dec[8:]
    counts = Counter(payload)
    print("Top 5 Byte Values (Frequency):")
    for b, count in counts.most_common(5):
        hex_val = hex(b)
        pct = (count / len(payload)) * 100
        print(f"  {hex_val}: {count} ({pct:.2f}%)")
    
else:
    print("No Zlib header found. Plain binary.")
