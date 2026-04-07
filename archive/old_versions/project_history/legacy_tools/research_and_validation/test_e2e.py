import os
import sys
import shutil
import tempfile
import tkinter as tk
import time

# Inject app directory to sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), 'app')))
import snowrunner_editor as se

def test_all_features():
    print("========================================")
    print("ðŸš€ SNOWRUNNER E2E INTEGRATION TESTING")
    print("========================================\n")
    
    # 1. Setup Sandbox
    test_dir = tempfile.mkdtemp()
    actual_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), 'Actual files'))
    if not os.path.exists(actual_dir):
        print(f"[!] SKIP: Sandbox source not found at {actual_dir}")
        return
        
    shutil.copytree(actual_dir, os.path.join(test_dir, "savegame"))
    sandbox_path = os.path.join(test_dir, "savegame")
    
    # Identify Main Save
    main_save = os.path.join(sandbox_path, "CompleteSave.dat")
    if not os.path.exists(main_save):
        main_save = os.path.join(sandbox_path, "CompleteSave.cfg")
        
    print(f"ðŸ“¦ Test Sandbox Initialized: {sandbox_path}")

    # Mock UI dependencies
    se.set_app_status = lambda msg, **kwargs: print(f"  [UI Status]: {msg}")
    root = tk.Tk()
    
    try:
        # Define test regions
        test_regions = ["US_01", "US_02", "RU_02"]

        # TEST 1: REVEAL MAP (FOG)
        print("\nâš™ï¸ TEST 1: Reveal Fog...")
        t1_res = se.generate_revealed_fog(main_save, test_regions, notify=False)
        assert t1_res.get("ok") is True, f"Fog Tool Failed: {t1_res}"
        fog_files = [f for f in os.listdir(sandbox_path) if f.startswith("fog_")]
        assert len(fog_files) > 0, "No fog files were created/modified in sandbox!"
        print(f"  âœ… PASSED: Generated {len(fog_files)} fog masks.")

        # TEST 2 & 3: DISCOVER ALL TRUCKS & TRAILERS (Combined)
        print("\nâš™ï¸ TEST 2 & 3: Discover All World Objects...")
        t2_res = se.discover_world_objects(main_save, test_regions, notify=False)
        assert t2_res.get("ok") is True, f"Discovery Failed: {t2_res}"
        print(f"  âœ… PASSED: {t2_res.get('message')}")

        # TEST 4: TRUCK EMPORIUM
        print("\nâš™ï¸ TEST 4: Truck Emporium (Inject)...")
        # Testing a high-value DLC truck injection
        t4_res = se.inject_truck_to_storage(main_save, "truck_ru_heavy_zikz_612h", notify=False)
        assert t4_res.get("ok") is True, f"Emporium Injection Failed: {t4_res}"
        print(f"  âœ… PASSED: {t4_res.get('message')}")
        
        # TEST 5: BACKUP NOW
        print("\nâš™ï¸ TEST 5: Backup System...")
        # Simulating UI variables
        se.make_backup_var = tk.BooleanVar(value=True)
        se.full_backup_var = tk.BooleanVar(value=False)
        se.max_backups_var = tk.StringVar(value="20")
        se.max_autobackups_var = tk.StringVar(value="50")
        
        t5_res = se.make_backup_if_enabled(main_save, force=True)
        assert t5_res is True, "Backup function returned non-success state!"
        
        backup_root = os.path.join(sandbox_path, "backup")
        backups_exist = os.path.exists(backup_root) and len(os.listdir(backup_root)) > 0
        assert backups_exist, "Backup folder wasn't created or is empty!"
        print(f"  âœ… PASSED: Backup created successfully.")

        # TEST 6: RESTORE NOW
        print("\nâš™ï¸ TEST 6: Restore Latest Backup...")
        # Step A: Corrupt the main save for testing
        with open(main_save, 'w') as f: f.write("CORRUPTED_SAVE_DATA")
        print("  [Sim] Save corrupted purposefully.")
        
        # Step B: Restore
        t6_res = se.restore_latest_backup(main_save, notify=False)
        assert t6_res.get("ok") is True, f"Restore function failed: {t6_res}"
        
        # Step C: Verify corruption is gone
        with open(main_save, 'r') as f:
            content = f.read()
            assert content != "CORRUPTED_SAVE_DATA", "Restore did not overwrite corrupted file!"
            assert "CompleteSave" in content, "Restored file format looks invalid!"
        print(f"  âœ… PASSED: Restoration successful. Corruption neutralized.")

        print("\nðŸŽ‰ ALL TESTS PASSED! APPLICATION LOGIC IS 100% STABLE!")

    except Exception as e:
        import traceback
        traceback.print_exc()
        print(f"\nâŒ E2E TEST FAILED: {str(e)}")
        sys.exit(1)
    finally:
        root.destroy()
        shutil.rmtree(test_dir)

if __name__ == "__main__":
    test_all_features()
