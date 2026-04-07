import sys
import os
import zlib
import struct

# Path setup
sys.path.append(os.path.join(os.getcwd(), 'app'))
from snowrunner_editor import generate_revealed_fog

test_file = r"e:\Snow Runner New Tool\remote\fog_level_us_01_01.dat"
region = ["US_01"]

print(f"Testing v110.6 Definitive Logic on {test_file}...")
res = generate_revealed_fog(test_file, region, notify=False)
print(f"Result: {res}")

with open(test_file, "rb") as f:
    data = f.read()
    if data.startswith(b'\x41\x4B\x05\x00'):
        dec = zlib.decompress(data[4:])
        from collections import Counter
        counts = Counter(dec[8:])
        print(f"Top Bytes: {counts.most_common(3)}")
        if counts[128] == len(dec[8:]):
            print("SUCCESS: 100% of map set to 128 (0x80)!")
        else:
            print(f"FAILURE: Found other bytes: {counts.most_common(5)}")
