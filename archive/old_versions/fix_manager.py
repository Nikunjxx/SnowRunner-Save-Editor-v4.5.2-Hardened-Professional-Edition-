import os, re
path = r'e:\Snow Runner New Tool\integrity_engine\manager.py'
with open(path, 'r', encoding='utf-8') as f: content = f.read()

# Pattern matches the tail of _revalidate_snapshot_post_commit 
# followed by the corrupted except/logging blocks
pattern = re.compile(
    r'(raise RuntimeError\(f\"Post-Commit Integrity Failure: Disk state drifted from snapshot for {conflicts}\"\))\s+(except Exception as e:.*?return result\s+)', 
    re.DOTALL
)

new_content = pattern.sub(r'\1\n\n    ', content)
if new_content != content:
    with open(path, 'w', encoding='utf-8') as f: f.write(new_content)
    print('Regex Cleanup successful')
else:
    print('Regex Match failed')
