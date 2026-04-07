import os

def final_inspect():
    base = r"C:\Program Files (x86)\Steam\userdata\996096852\1465360\remote"
    path = os.path.join(base, "CompleteSave.cfg")
    
    if os.path.exists(path):
        with open(path, "rb") as f:
            raw = f.read(100)
        print(f"CompleteSave.cfg Raw: {raw}")
        print(f"CompleteSave.cfg Hex: {raw.hex(' ')}")
    else:
        print("CompleteSave.cfg NOT FOUND")

if __name__ == "__main__":
    final_inspect()
