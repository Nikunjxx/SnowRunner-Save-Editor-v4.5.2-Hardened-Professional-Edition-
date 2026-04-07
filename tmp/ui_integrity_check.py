import sys
import os
import json
from pprint import pprint

# Ensure we're in the right path for imports
sys.path.append(os.getcwd())

def ui_integrity_test():
    print("--- [ 🏢 UI Integrity Self-Test (Objectives+) ] ---")
    
    # 1. Initialize DB
    from data.objective_database import get_objective_db
    db = get_objective_db()
    
    print("\n[Step 1/3] Loading Mission Catalog...")
    if not db.load_local(allow_build=False):
        print("⏳ Catalog not found. Running web sync...")
        db.refresh_from_web(use_safe_fallback=True)
        db.load_local()
    
    print(f"Catalog Loaded: {len(db.raw_list or [])} items discovered.")
    
    # 2. Initialize IntegrityManager with user path
    from integrity_engine.manager import IntegrityManager
    user_path = r'C:\Program Files (x86)\Steam\userdata\996096852\1465360\remote'
    data_dir = os.path.join(os.path.expanduser("~"), "snowrunner_save_editor_data")
    os.makedirs(data_dir, exist_ok=True)
    
    print(f"\n[Step 2/3] Initializing IntegrityManager with target folder...")
    # IntegrityManager(target_folder, data_dir, remote2_path)
    # Using target_folder as remote2_path is not needed for this check
    try:
        manager = IntegrityManager(user_path, data_dir, user_path)
        print(f"Manager initialized successfully.")
        ctx = manager.get_save_context()
        active_slot = ctx['slot']['active']
        print(f"Active Slot: {active_slot}")
        
        # 3. Simulate ObjectivesPlugin synchronization
        print("\n[Step 3/3] Simulating Objectives+ Synchronization...")
        
        # Mimic ObjectivesPlugin.get_progression_data logic
        # get_progression_data(plugin_ref) -> context calls _find_finished_ids or similar
        # In current plugin: finished_ids = set(analytics.get("unknown_in_save", []))
        
        finished_ids = set()
        if 'meta' in ctx and 'finished_objs' in ctx['meta']:
            finished_ids = set(ctx['meta']['finished_objs'])
            print(f"Discovered {len(finished_ids)} finished objectives in save file.")
        
        # Test mapping
        matches = 0
        samples = []
        for it in db.raw_list[:1000]: # Sample first 1000
            if it['key'] in finished_ids:
                matches += 1
                if len(samples) < 5:
                    samples.append(f"{it['displayName']} ({it['key']})")
                    
        print(f"Integration Check: {matches} missions matched with catalog.")
        if samples:
            print("\nRecent Completions Matched:")
            for s in samples:
                print(f"  - {s}")
        
        print("\n✅ UI INTEGRITY SELF-TEST PASSED")
        
    except Exception as e:
        print(f"\n❌ UI INTEGRITY SELF-TEST FAILED: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    ui_integrity_test()
