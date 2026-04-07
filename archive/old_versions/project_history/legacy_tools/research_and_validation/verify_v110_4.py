import sys
import os
import zlib
import struct

# Path setup
sys.path.append(os.path.join(os.getcwd(), 'app'))
from snowrunner_editor import generate_revealed_fog

test_file = r"e:\Snow Runner New Tool\remote\fog_level_ru_02_01.dat"
region = ["RU_02"] # Quarry is RU_02

print(f"Testing v110.4 Patch Logic on {test_file}...")
res = generate_revealed_fog(test_file, region, notify=False)
print(f"Result: {res}")

# Now inspect if it's 0x80 instead of 0x00
with open(test_file, "rb") as f:
    data = f.read()
    if data.startswith(b'\x41\x4B\x05\x00'):
        dec = zlib.decompress(data[4:])
        print(f"First 16 bytes (Header + Payload): {dec[:16].hex(' ')}")
        if dec[8] == 0x80:
            print("SUCCESS: Byte 0x80 (Revealed) is present!")
        else:
            print(f"FAILURE: Byte {hex(dec[8])} found instead of 0x80.")
