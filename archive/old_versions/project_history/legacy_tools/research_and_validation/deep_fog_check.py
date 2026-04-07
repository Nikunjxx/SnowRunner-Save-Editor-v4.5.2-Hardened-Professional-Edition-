import zlib
import struct
import binascii

f_path = r"e:\Snow Runner New Tool\remote\fog_level_us_01_01.dat"
print(f"Deep Analysis of {f_path}...")
with open(f_path, "rb") as f:
    data = f.read()

if data.startswith(b'AK\x05\x00'):
    dec = zlib.decompress(data[4:])
    print(f"Header: {binascii.hexlify(dec[:16], ' ')}")
    w, h = struct.unpack("<II", dec[:8])
    print(f"Dimensions: {w}x{h}")
    # Check if there is a 3rd field in the header
    v1, v2, v3, v4 = struct.unpack("<IIII", dec[:16])
    print(f"Full Header: {v1}, {v2}, {v3}, {v4}")
    
    # Check first 64 bytes of pixel data
    pixels = dec[16:80]
    print(f"First 64 Pixel Bytes: {binascii.hexlify(pixels, ' ')}")
    
    # Check common values
    from collections import Counter
    counts = Counter(dec[16:])
    print("Common Bytes:")
    for b, count in counts.most_common(10):
        print(f"  {hex(b)}: {count}")
else:
    print("Not Zlib.")
