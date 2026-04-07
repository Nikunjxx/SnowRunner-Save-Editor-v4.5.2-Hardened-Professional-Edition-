import os
import zlib
from collections import Counter

remote_dir = r"e:\Snow Runner New Tool\remote"
f_files = [f for f in os.listdir(remote_dir) if f.startswith('fog_') and f.endswith('.dat')]

print(f"Scanning {len(f_files)} fog files in remote folder...")

for fname in f_files:
    f_path = os.path.join(remote_dir, fname)
    with open(f_path, "rb") as f:
        data = f.read()
    
    if data.startswith(b'\x41\x4B\x05\x00'):
        try:
            dec = zlib.decompress(data[4:])
            # Filter out 0xFF (Fog) to see what 'Revealed' looks like
            revealed_bytes = [b for b in dec[8:] if b != 0xFF]
            counts = Counter(revealed_bytes)
            top = counts.most_common(2)
            print(f"{fname}: Size={len(dec)} Top Revealed={top}")
        except:
            print(f"{fname}: Decompression failed.")
    else:
        print(f"{fname}: No Zlib Header.")
