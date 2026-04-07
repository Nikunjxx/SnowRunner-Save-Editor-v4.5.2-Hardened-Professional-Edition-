import os

target = r"e:\Snow Runner New Tool\app\snowrunner_editor.py"
with open(target, "r", encoding="utf-8") as f:
    content = f.read()

# 1. Overhaul discover_world_objects (v110.7 - Deep Region Discovery)
# Replacing the entire function with one that adds map registrations
new_discover_func = r'''def discover_world_objects(save_path, selected_regions, notify=True):
    """
    v110.7 Deep Discovery: Not only unlocks Trucks/Upgrades but also registers the 
    Maps themselves in discoveredMaps, visitedLevels, and knowMap. 
    This ensures the Region appears on the Global Map and selector.
    """
    try:
        with open(save_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        counts = {"new": 0, "maps": 0}
        
        # Lists for deep region registration
        map_registries = ["discoveredMaps", "visitedLevels", "knowMap"]
        # Lists for world object discovery
        object_registries = [
            "discoveredTrucks", "discoveredUpgrades", "discoveredTrailers", 
            "discoveredObjects", "viewedUnactivatedObjectives"
        ]

        # Ensure registries exist
        for reg in map_registries + object_registries:
            if reg not in data["CompleteSave"]:
                data["CompleteSave"][reg] = []

        for code in selected_regions:
            ids = OBJECT_DATABASE.get(code, [])
            # 1. Inject World Objects
            for obj_id in ids:
                for reg in object_registries:
                    if obj_id not in data["CompleteSave"][reg]:
                        data["CompleteSave"][reg].append(obj_id)
                        counts["new"] += 1
            
            # 2. Inject Map Registrations (v110.7)
            # Fetch all levels associated with this region
            levels = REGION_LEVELS.get(code, [])
            for lvl_id in levels:
                for reg in map_registries:
                    if lvl_id not in data["CompleteSave"][reg]:
                        data["CompleteSave"][reg].append(lvl_id)
                        counts["maps"] += 1

        with open(save_path, 'w', encoding='utf-8') as f:
            json.dump(data, f)
            
        msg = f"Deep Unlocked {counts['new']} objects and registered {counts['maps']} maps for {len(selected_regions)} regions."
        return _action_result("Success", msg, notify=notify)
    except Exception as e:
        return _action_result("Error", str(e), notify=notify)'''

# Marker-based replacement
start_marker = 'def discover_world_objects(save_path, selected_regions, notify=True):'
end_marker = 'return _action_result("Success", msg, notify=notify)'

start_idx = content.find(start_marker)
end_idx = content.find(end_marker, start_idx)

if start_idx != -1 and end_idx != -1:
    content = content[:start_idx] + new_discover_func + content[end_idx + len(end_marker):]
    print("Injected v110.7 deep discovery logic.")

# 2. Version Bump to v110.7
content = content.replace('APP_VERSION = 110.6', 'APP_VERSION = 110.7')

with open(target, "w", encoding="utf-8") as f:
    f.write(content)
print("v110.7 deployment successfully patched.")
