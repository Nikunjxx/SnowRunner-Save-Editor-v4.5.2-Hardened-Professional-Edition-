# [PH4-VER-SUP] Phase 4.5.2 Support & UX Audit
import sys
import os
import tkinter as tk
import glob

# Absolute Pathing [PH4-ARCH-ROOT]
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from core_engineering.engine.transaction_manager import SaveTransactionManager
from core_engineering.engine.save_adapter import SaveAdapter
from ui.main_window import SnowRunnerEditorUI

def run_support_audit():
    print("Initiating Phase 4.5.2 Support & UX Audit...")
    
    # --- DRILL 1: TIMESTAMPED BACKUPS ---
    print("\nDRILL 1: Verifying Timestamped Backup Naming...")
    adapter = SaveAdapter()
    tx_mgr = SaveTransactionManager(adapter)
    
    test_file = "e:/Snow Runner New Tool/scripts/test_save.cfg"
    with open(test_file, "w") as f: f.write("{}")
    
    tx_mgr.execute(test_file, {"player.money": 500})
    
    # Find backups
    backups = glob.glob(test_file + "_*.bak")
    if backups:
         print(f"DRILL 1 SUCCESS: Timestamped backup created: {os.path.basename(backups[0])}")
    else:
         print("DRILL 1 FAILURE: No timestamped backup found!")
         return
         
    # Cleanup
    for b in backups: os.remove(b)
    os.remove(test_file)

    # --- DRILL 2: UI BRANDING ---
    print("\nDRILL 2: Verifying Version Branding...")
    root = tk.Tk()
    app = SnowRunnerEditorUI(root)
    
    title = root.title()
    if "v4.5.2" in title and "Hardened" in title:
         print(f"DRILL 2 SUCCESS: Professional Branding confirmed: '{title}'")
    else:
         print(f"DRILL 2 FAILURE: Branding mismatch or missing: '{title}'")
         return

    print("\n--- PHASE 4.5.2 AUDIT COMPLETE: APP IS PRODUCTION-POLISHED ---")
    root.destroy()

if __name__ == "__main__":
    run_support_audit()
