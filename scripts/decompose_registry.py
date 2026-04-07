import json
import yaml
import os

REGISTRY_PATH = r"E:\Snow Runner New Tool\core_engineering\data\maprunner_registry.json"
OUTPUT_DIR = r"E:\Snow Runner New Tool\core_engineering\maprunner\registry"

if not os.path.exists(OUTPUT_DIR):
    os.makedirs(OUTPUT_DIR)

print(f"Loading {REGISTRY_PATH}...")
with open(REGISTRY_PATH, 'r') as f:
    data = json.load(f)

# 1. Regions
print("Extracting Regions...")
regions = data.get('regions', {})
with open(os.path.join(OUTPUT_DIR, "regions.yaml"), 'w') as f:
    yaml.dump(regions, f, sort_keys=False)

# 2. Objectives (Maps/Contracts)
print("Extracting Objectives and Map Structure...")
objectives = data.get('objectives', {})
with open(os.path.join(OUTPUT_DIR, "contracts.yaml"), 'w') as f:
    yaml.dump(objectives, f, sort_keys=False)

# 3. Reference Data Merging (Optional)
# If upgrades or trucks are missing from main registry, we seed from references
REF_UPGRADES_PATH = r"E:\Snow Runner New Tool\core_engineering\snowrunner_save_editor_data\reference_upgrades.json"
if os.path.exists(REF_UPGRADES_PATH):
    print("Seeding Upgrades from reference data...")
    with open(REF_UPGRADES_PATH, 'r') as f:
        upgrades = json.load(f)
    with open(os.path.join(OUTPUT_DIR, "upgrades.yaml"), 'w') as f:
        yaml.dump(upgrades, f, sort_keys=False)

# 4. Initialize Placeholder for Trucks (Manual entry needed for full Phase 3)
trucks = {
    "western_star_4964": {"name": "Western Star 4964", "type": "heavy"},
    "chevrolet_ck1500": {"name": "Chevrolet CK1500", "type": "scout"},
    "fleetstar_f2070a": {"name": "Fleetstar F2070A", "type": "heavy"},
    "gmc_mh9500": {"name": "GMC MH9500", "type": "heavy_duty"}
}
with open(os.path.join(OUTPUT_DIR, "trucks.yaml"), 'w') as f:
    yaml.dump(trucks, f, sort_keys=False)

print("Decomposition Complete.")
