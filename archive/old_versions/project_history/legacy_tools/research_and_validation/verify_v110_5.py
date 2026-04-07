import sys
import os
import zlib
import struct

# Path setup
sys.path.append(os.path.join(os.getcwd(), 'app'))
from snowrunner_editor import generate_revealed_fog

test_file = r"e:\Snow Runner New Tool\remote\fog_level_us_01_01.dat"
region = ["US_01"] # Michigan is US_01

print(f"Testing v110.5 Patch Logic on {test_file}...")
# This will decompress, patch only 0xFF to 0x00, and re-compress
res = generate_revealed_fog(test_file, region, notify=False)
print(f"Result: {res}")

# Now inspect if the header (589x589) is still there
with open(test_file, "rb") as f:
    data = f.read()
    if data.startswith(b'\x41\x4B\x05\x00'):
        dec = zlib.decompress(data[4:])
        import struct
        w, h = struct.unpack("<II", dec[:8])
        print(f"Header: {w}x{h}")
        # Pixel check: Should contain 0x00 (new) and 0x80 (old manual reveal)
        first_pixels = dec[12:32] # skip the possible 12-byte header
        print(f"Pixels (Hex): {first_pixels.hex(' ')}")
        if w == 589 and h == 589:
            print("SUCCESS: Header 589x589 preserved!")
        else:
            print(f"FAILURE: Header corrupted to {w}x{h}")
