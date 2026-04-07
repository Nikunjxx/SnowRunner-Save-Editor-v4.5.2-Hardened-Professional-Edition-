import os
import time
import sys

# Add current dir to path
sys.path.append(os.getcwd())

from integrity_engine.manager import get_integrity_manager

APP_DATA_DIR = os.path.join(os.path.expanduser("~"), "snowrunner_save_editor_data")
REMOTE2_PATH = os.path.join(os.getcwd(), "remote2", "remote")
TARGET_DIR = r"E:\Snow Runner New Tool\example_save_folder" # Adjust to a real save folder if testing locally

def run_diagnostic():
    print("--- FIRST LOAD DIAGNOSTIC ---")
    
    # 1. Clean pattern cache to simulate "first run"
    cache_file = os.path.join(APP_DATA_DIR, "reference_patterns.json")
    if os.path.exists(cache_file):
        print(f"Clearing cache: {cache_file}")
        os.remove(cache_file)
    
    start_time = time.time()
    
    print("Step 1: Initializing IntegrityManager (Pass 0: Pattern Extraction)...")
    m_start = time.time()
    manager = get_integrity_manager(TARGET_DIR, APP_DATA_DIR, REMOTE2_PATH)
    m_end = time.time()
    print(f"IntegrityManager __init__ took: {m_end - m_start:.2f}s")
    
    print("Step 2: Starting Hydration (Pass 1-5)...")
    h_start = time.time()
    manager._hydrate_context(progress_callback=lambda msg, val: print(f"  [Progress] {msg} ({val*100:.0f}%)"))
    h_end = time.time()
    print(f"Hydration took: {h_end - h_start:.2f}s")
    
    # 3. Check Objective Database
    from data.objective_database import get_objective_db
    print("Step 3: Loading Objective Catalog (Singleton)...")
    db_start = time.time()
    db = get_objective_db()
    db.load_local()
    db_end = time.time()
    print(f"Objective Database load_local took: {db_end - db_start:.2f}s")
    
    total = time.time() - start_time
    print(f"--- TOTAL FIRST LOAD TIME: {total:.2f}s ---")

if __name__ == "__main__":
    # Ensure some folders exist for the test
    os.makedirs(APP_DATA_DIR, exist_ok=True)
    if os.path.exists(TARGET_DIR):
        run_diagnostic()
    else:
        print(f"Skipping diagnostic: {TARGET_DIR} not found.")
