import os
import sys
import json
import time

# Ensure project modules are in path
sys.path.append(r"e:\Snow Runner New Tool")

from integrity_engine.manager import IntegrityManager

def run_diagnostic():
    print("="*60)
    print(" SNOWRUNNER EDITOR v112.30 - FULL SELF-TEST DIAGNOSTIC")
    print("="*60)
    
    target_path = r"C:\Program Files (x86)\Steam\userdata\996096852\1465360\remote"
    data_dir = os.path.join(os.environ['USERPROFILE'], "snowrunner_save_editor_data")
    
    if not os.path.isdir(target_path):
        print(f"FAILED: Path not accessible: {target_path}")
        return

    print(f"Source Folder: {target_path}")
    print(f"Data Dir: {data_dir}")
    print("-" * 30)

    try:
        # Initialize Manager (Triggers 5-Pass Hydration)
        start_t = time.time()
        manager = IntegrityManager(target_path, data_dir, target_path)
        ctx = manager.save_context
        duration = (time.time() - start_t) * 1000
        
        print(f"Hydration Timing: {duration:.2f}ms")
        print("-" * 30)

        # 1. Slot Check
        print(f"[SLOT] Active: {ctx['slot']['active']}")
        print(f"[SLOT] Available: {ctx['slot']['available']}")

        # 2. Player Stats
        p = ctx['player']
        print(f"[PLAYER] Bank: ${p['money']:,}")
        print(f"[PLAYER] Rank: {p['rank']}")
        print(f"[PLAYER] XP: {p['experience']}")

        # 3. Regional Coverage
        regions = ctx['regions']
        print(f"[WORLD] Regions Indexed: {len(regions)}")
        for rname, rinfo in regions.items():
            maps = rinfo['maps']
            visited = sum(1 for m in maps.values() if m['progression']['visited'])
            unlocked = sum(1 for m in maps.values() if m['progression']['unlocked'])
            print(f"  - {rname}: {unlocked}/{len(maps)} Unlocked | {visited} Visited")

        # 4. Objective Accuracy (Sample)
        print("-" * 30)
        total_objs = sum(m['objectives']['total'] for r in regions.values() for m in r['maps'].values())
        print(f"[STORY] Total Objectives Discovered (Binary STS): {total_objs}")
        
        # Sample one map if possible
        michigan = regions.get("Michigan", {}).get("maps", {}).get("Black River", {})
        if michigan:
            print(f"  - (Michigan) Black River: {michigan['objectives']['total']} objectives found.")
            if michigan['objectives']['list']:
                print(f"    Sample ID: {michigan['objectives']['list'][0]}")

        print("-" * 30)
        print("DIAGNOSTIC COMPLETE - NO FATAL ERRORS")
        print("="*60)

    except Exception as e:
        print(f"CRITICAL SYSTEM FAILURE: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    run_diagnostic()
