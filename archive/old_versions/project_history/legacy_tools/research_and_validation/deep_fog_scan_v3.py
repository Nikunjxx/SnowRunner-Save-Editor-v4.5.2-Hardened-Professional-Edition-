import os, zlib, struct

def scan_fog_files(directory):
    print(f"{'Filename':<30} | {'Uncomp Size':<12} | {'Width':<6} | {'Height':<6}")
    print("-" * 65)
    for f in os.listdir(directory):
        if f.startswith("fog_") and f.endswith(".dat"):
            path = os.path.join(directory, f)
            with open(path, "rb") as fh:
                data = fh.read()
            if not data.startswith(b"\x41\x4B\x05\x00"):
                continue
            try:
                dec = zlib.decompress(data[4:])
                w, h = struct.unpack("<II", dec[:8])
                print(f"{f:<30} | {len(dec):<12,} | {w:<6} | {h:<6}")
            except Exception as e:
                print(f"{f:<30} | FAILED ({e})")

scan_fog_files("e:/Snow Runner New Tool/research_and_validation")
