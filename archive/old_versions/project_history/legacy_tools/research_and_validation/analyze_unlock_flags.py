import re
import json

path = r"e:\Snow Runner New Tool\Actual files\CompleteSave.dat"
print(f"Analyzing {path} for Region Unlocking flags...")

with open(path, "rb") as f:
    data = f.read()[4:].decode("utf-8", errors="ignore")

# Find key lists
keys = [
    "discoveredMaps",
    "visitedLevels",
    "viewedUnactivatedObjectives",
    "discoveredWatchtowers"
]

for key in keys:
    match = re.search(f'"{key}":\\[(.*?)\\]', data)
    if match:
        print(f"\n[{key}] Sample Content:")
        print(f"  {match.group(1)[:300]}...")
    else:
        print(f"\n[{key}] NOT FOUND")
