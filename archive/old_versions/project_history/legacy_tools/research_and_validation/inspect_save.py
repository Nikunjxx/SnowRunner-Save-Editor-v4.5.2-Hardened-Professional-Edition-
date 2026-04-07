import zlib
import os

f_path = r"e:\Snow Runner New Tool\remote\CompleteSave.cfg"
with open(f_path, "rb") as f:
    data = f.read()

if data.startswith(b'AK\x05\x00'):
    content = zlib.decompress(data[4:])
    with open(r"e:\Snow Runner New Tool\remote_save_decompressed.json", "wb") as f:
        f.write(content)
    print("Decompressed save to remote_save_decompressed.json")
else:
    print("Not Zlib compressed.")
