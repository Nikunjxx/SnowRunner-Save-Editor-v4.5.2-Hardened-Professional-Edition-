import sys
import os
from pprint import pprint

# Ensure we're in the right path for imports
sys.path.append(os.getcwd())

def test_db():
    print("--- [ 🎯 ObjectiveDatabase Verification ] ---")
    from data.objective_database import get_objective_db
    db = get_objective_db()

    print(f"Cache Path: {db.csv_path}")
    
    # FORCE REFRESH
    print("\nForcing a fresh web sync...")
    if os.path.exists(db.csv_path):
        os.remove(db.csv_path)
    
    success = db.refresh_from_web(use_safe_fallback=True)
    print(f"Web Refresh Success: {success}")
    
    if not success:
        print("❌ FAILED TO FETCH DATA")
        return

    db.load_local()

    if db.raw_list:
        print(f"Found {len(db.raw_list)} objectives.")
        
        # Search for a Task vs Contract to verify classification
        tasks = [r for r in db.raw_list if r.get('type') == 'TASK']
        contracts = [r for r in db.raw_list if r.get('type') == 'CONTRACT']
        contests = [r for r in db.raw_list if r.get('type') == 'CONTEST']
        print(f"\nStats:")
        print(f"  Tasks: {len(tasks)}")
        print(f"  Contracts: {len(contracts)}")
        print(f"  Contests: {len(contests)}")
        
        # Check for non-empty fields in a few samples
        samples = db.raw_list[:3]
        for it in samples:
            print(f"\nSample: {it.get('displayName')} ({it.get('key')})")
            print(f"  Type: {it.get('type')}")
            print(f"  Rewards: ${it.get('money')} / {it.get('experience')} XP")
            print(f"  Cargo: {it.get('cargo_needed') or 'None'}")
            print(f"  Region: {it.get('region_name')}")

        # Search for cargo delivery specifically
        cargo_items = [r for r in db.raw_list if r.get('cargo_needed')]
        if cargo_items:
            print(f"\nFound {len(cargo_items)} missions requiring cargo.")
            pprint(cargo_items[0])
    else:
        print("❌ DATABASE IS EMPTY")

if __name__ == "__main__":
    test_db()
