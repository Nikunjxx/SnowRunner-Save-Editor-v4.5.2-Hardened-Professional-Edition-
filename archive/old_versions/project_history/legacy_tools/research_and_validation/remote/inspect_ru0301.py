import os, zlib, struct

def inspect_file(path):
    print(f"Inspecting: {path}")
    if not os.path.exists(path):
        print("File not found.")
        return
    
    with open(path, "rb") as f:
        data = f.read()
    
    print(f"File size: {len(data)} bytes")
    if data.startswith(b"\x41\x4B\x05\x00"):
        try:
            dec = zlib.decompress(data[4:])
            print(f"Decompressed size: {len(dec)} bytes")
            if len(dec) >= 8:
                w, h = struct.unpack("<II", dec[:8])
                print(f"Dimensions from header: {w}x{h}")
                print(f"Expected payload: {w*h} bytes")
                print(f"Actual payload: {len(dec) - 8} bytes")
                if len(dec) - 8 == w*h:
                    print("Data length matches header.")
                else:
                    print("DATA LENGTH MISMATCH!")
        except Exception as e:
            print(f"Decompression error: {e}")
    else:
        print("Not a standard compressed fog/save file.")

inspect_file("e:/Snow Runner New Tool/research_and_validation/remote/fog_level_ru_03_01.cfg")
