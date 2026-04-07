import os
import zlib
import json

def inspect_save():
    path = r"C:\Program Files (x86)\Steam\userdata\996096852\1465360\remote\CompleteSave.cfg"
    if not os.path.exists(path):
        print("File not found.")
        return

    print("=" * 60)
    print(f"DEEP INSPECTION: {path}")
    print("=" * 60)
    
    with open(path, "rb") as f:
        raw = f.read()

    print(f"Total Disk Size: {len(raw)} bytes")
    print(f"Header (Hex): {raw[:16].hex(' ')}")
    
    try:
        payload = zlib.decompress(raw[4:])
        print(f"Decompression: SUCCESS ({len(payload)} bytes)")
        
        # Check if it starts with { (JSON) or something else
        sample = payload[:500]
        print(f"Payload Start: {sample[:100]}")
        print("-" * 30)
        
        # Log common markers in binary
        for marker in [b"money", b"rank", "experience", "finishedObjs"]:
            if isinstance(marker, str): marker = marker.encode('utf-8')
            pos = payload.find(marker)
            print(f"Find '{marker.decode()}': {'FOUND at ' + str(pos) if pos != -1 else 'NOT FOUND'}")

        # Final Attempt: String Dump (Alpha only)
        import re
        all_strings = re.findall(b"[a-zA-Z0-9_]{4,}", payload)
        print(f"Total Alphanumeric Strings found: {len(all_strings)}")
        print(f"Sample Strings: {all_strings[:20]}")

    except Exception as e:
        print(f"Decompression FAIL: {e}")

if __name__ == "__main__":
    inspect_save()
