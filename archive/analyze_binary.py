import os
import zlib
import json
import struct
import re

def d(p):
    with open(p, "rb") as f:
        r = f.read()
    try:
        return zlib.decompress(r[4:])
    except:
        return None

def analyze_binary_sts(data):
    # Extract strings (alphanumeric + underscore, length > 3)
    strings = re.findall(b"[a-zA-Z0-9_]{4,}", data)
    unique_strings = []
    for s in strings:
        if s not in unique_strings:
            unique_strings.append(s.decode('utf-8', errors='ignore'))
    
    # Look for common SnowRunner patterns
    # Often strings are prefixed by a 4-byte length
    patterns = []
    for s in strings:
        idx = data.find(s)
        if idx >= 4:
            length_prefix = struct.unpack("<I", data[idx-4:idx])[0]
            if length_prefix == len(s):
                patterns.append({"string": s.decode('utf-8'), "offset": idx, "prefix_match": True})
    
    return {
        "total_len": len(data),
        "string_count": len(strings),
        "unique_strings_sample": unique_strings[:50],
        "length_prefixed_samples": patterns[:10]
    }

def analyze_binary_fog(data):
    return {
        "total_len": len(data),
        "hex_sample": data[:128].hex(),
        "strings": [s.decode('utf-8', errors='ignore') for s in re.findall(b"[a-zA-Z0-9_]{4,}", data)]
    }

if __name__ == "__main__":
    TARGET = r"e:\Snow Runner New Tool\remote2\remote"
    
    # Analyze STS
    sts_path = os.path.join(TARGET, "sts_level_us_01_01.cfg")
    sts_raw = d(sts_path)
    sts_report = analyze_binary_sts(sts_raw) if sts_raw else "FAILED"
    
    # Analyze Fog
    fog_path = os.path.join(TARGET, "fog_level_us_01_01.cfg")
    fog_raw = d(fog_path)
    fog_report = analyze_binary_fog(fog_raw) if fog_raw else "FAILED"
    
    print(json.dumps({
        "STS": sts_report,
        "Fog": fog_report
    }, indent=2))
