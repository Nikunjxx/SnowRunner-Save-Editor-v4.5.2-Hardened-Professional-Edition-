# [PH4-VER-DISK] Phase 4.2 Mission-Safe Verification
import sys
import os
import shutil
import json

# Absolute Pathing
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "core_engineering")))

from maprunner.maprunner import MapRunner
from mapper.validators import FieldValidator
from engine.mutation_engine import MutationEngine
from engine.save_adapter import SaveAdapter
from engine.transaction_manager import SaveTransactionManager

def run_verify_4_2():
    print("Initiating Phase 4.2 Disk Safety Audit...")
    
    # 1. Component Load
    mpr = MapRunner()
    validator = FieldValidator(mpr)
    engine = MutationEngine(mpr, validator)
    adapter = SaveAdapter()
    tx_mgr = SaveTransactionManager(adapter)
    
    # 2. Setup Mock Target
    test_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "temp_audit"))
    if not os.path.exists(test_dir): os.makedirs(test_dir)
    
    test_path = os.path.join(test_dir, "test_save.dat")
    initial_state = {
        "derived.player.money": 100,
        "derived.player.rank": 1,
        "CompleteSave.SslValue.persistentProfileData.trucksInWarehouse": [
            {"type": "ws_4964_white", "isUnlocked": True}
        ]
    }
    adapter.write(test_path, initial_state)
    
    # --- STAGE 1: THE CENTURY RUN (100 Cycles) ---
    print("\nSTAGE 1: Executing 100 read-write cycles...")
    for i in range(100):
        # Read
        state = adapter.read(test_path)
        engine.set_state(state)
        
        # Edit
        engine.apply_change("player.money", 100 + i)
        
        # Transaction
        res = tx_mgr.execute(test_path, engine.state)
        if res["status"] != "COMMITTED":
            print(f"CRITICAL FAILURE at cycle {i}: {res.get('error') or res.get('reason')}")
            return
            
        if i % 20 == 0: print(f"Cycle {i}/100 Complete.")
    print("STAGE 1 SUCCESS: No bit-drift detected.")
    
    # --- STAGE 2: FORCED CORRUPTION (Rollback Test) ---
    print("\nSTAGE 2: Forced Corruption recovery test...")
    # We'll mock the adapter to fail during write
    original_write = adapter.write
    def corrupt_write(path, state):
        # Write corrupted garbage bytes
        with open(path, "wb") as f: f.write(b"{corrupted_json_garbage\x01\x02")
    
    adapter.write = corrupt_write
    
    # Get current state
    state = adapter.read(test_path)
    engine.set_state(state)
    engine.apply_change("player.money", 999999)
    
    res = tx_mgr.execute(test_path, engine.state)
    
    # Restore original write for cleanup
    adapter.write = original_write
    
    if res["status"] == "ROLLED_BACK":
        print(f"STAGE 2 SUCCESS: Corruption detected, safely rolled back. (Reason: {res['error']})")
        # Verify original file parity
        final_state = adapter.read(test_path)
        if final_state["derived.player.money"] != 199: # Last valid cycle from Stage 1
             print(f"ERROR: Original file was modified despite rollback! Value: {final_state['derived.player.money']}")
             return
        print("STAGE 2 VERIFIED: Original file remains untouched (Identity-Lock preserved).")
    else:
        print("STAGE 2 FAILURE: System committed corrupted data!")
        return

    print("\n--- PHASE 4.2 AUDIT COMPLETE: MISSION READY ---")

if __name__ == "__main__":
    run_verify_4_2()
