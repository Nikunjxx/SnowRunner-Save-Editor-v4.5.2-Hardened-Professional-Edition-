import json
from slot_resolver import SlotResolver
from hydration import SaveLoader, FieldAccessor

def main():
    folder_path = r"E:\Snow Runner New Tool\remote2\remote"
    print(f"Testing Hydration against: {folder_path}")
    
    slots = SlotResolver.scan_folder(folder_path)
    print(f"Found {len(slots)} active slots.")
    
    for slot in slots:
        print(f"\n--- [ SLOT {slot.slot_index + 1} (Prefix '{slot.prefix}') ] ---")
        print(f"Platform: {'Epic (.dat)' if slot.is_epic else 'Steam (.cfg)'}")
        
        files = SlotResolver.get_slot_files(slot)
        
        print("Associated STS Binary Files:", len(files["sts"]))
        print("Associated FOG Binary Files:", len(files["fog"]))
        
        core_save = files["core"].get("CompleteSave")
        if core_save:
            print(f"Hydrating: {core_save}")
            try:
                raw_json = SaveLoader.read_json_safe(core_save)
                accessor = FieldAccessor(raw_json)
                money = accessor.get_money()
                exp = accessor.get_experience()
                visited = len(accessor.get_visited_levels())
                print(f"  SUCCESS! -> Bank: ${money} | Rank XP: {exp} | Visited Maps: {visited}")
            except Exception as e:
                print(f"  ERROR: {e}")

if __name__ == "__main__":
    main()
