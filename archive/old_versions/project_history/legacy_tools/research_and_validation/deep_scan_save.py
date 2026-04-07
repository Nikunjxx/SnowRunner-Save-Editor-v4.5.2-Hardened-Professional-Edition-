import zlib
import os
import re

remote_dir = r"e:\Snow Runner New Tool\remote"
files = [f for f in os.listdir(remote_dir) if f.endswith('.cfg')]

for fname in files:
    f_path = os.path.join(remote_dir, fname)
    try:
        with open(f_path, "rb") as f:
            data = f.read()
        
        if data.startswith(b'AK\x05\x00'):
            content = zlib.decompress(data[4:]).decode('utf-8', errors='ignore')
            # Look for money/level
            money = re.search(r'"money"\s*:\s*(\d+)', content, re.IGNORECASE)
            level = re.search(r'"rank"\s*:\s*(\d+)', content, re.IGNORECASE)
            exp = re.search(r'"experience"\s*:\s*(\d+)', content, re.IGNORECASE)
            
            if money or level or exp:
                print(f"FOUND DATA in {fname}:")
                if money: print(f"  Money: {money.group(1)}")
                if level: print(f"  Rank: {level.group(1)}")
                if exp: print(f"  Exp: {exp.group(1)}")
            else:
                # Still check if it contains the word money at all
                if "money" in content.lower():
                    print(f"File {fname} contains 'money' but no value match.")
        else:
            # Plain text
            content = data.decode('utf-8', errors='ignore')
            money = re.search(r'"money"\s*:\s*(\d+)', content, re.IGNORECASE)
            if money:
                 print(f"FOUND DATA in Plain Text {fname}: Money: {money.group(1)}")

    except Exception as e:
        print(f"Error reading {fname}: {e}")
