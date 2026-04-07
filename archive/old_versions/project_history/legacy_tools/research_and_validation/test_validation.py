import os
import sys
import tkinter as tk
import tempfile
import shutil

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), 'app')))
import snowrunner_editor as se

def test_dynamic_scanner():
    print("[TEST] Running Dynamic Scanner Test...")
    actual_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), 'Actual files'))
    if not os.path.exists(actual_dir):
        print(f"Skipping scanner test; {actual_dir} not found.")
        return
    
    # Test Michigan 04 with 'new' suffix
    michigan_04 = se._find_best_map_files(actual_dir, "", "fog_", "level_us_01_04")
    assert "fog_level_us_01_04_new.dat" in michigan_04[0], f"Failed to pick up new.dat, got: {michigan_04}"
    
    # Test Alaska 01 without 'new' suffix
    alaska_01 = se._find_best_map_files(actual_dir, "", "fog_", "level_us_02_01")
    assert "fog_level_us_02_01.dat" in alaska_01[0], f"Failed to pick up base .dat, got: {alaska_01}"
    
    # Test Taymyr 01 crop variant
    taymyr_01 = se._find_best_map_files(actual_dir, "", "fog_", "level_ru_02_01")
    assert "fog_level_ru_02_01_crop.dat" in taymyr_01[0], f"Failed to pick up crop variant, got: {taymyr_01}"

    # Test Unvisited Map (should create a fallback base .dat)
    unvisited = se._find_best_map_files(actual_dir, "", "fog_", "level_fake_99_99")
    assert "fog_level_fake_99_99.dat" in unvisited[0], f"Fallback base file generation failed, got: {unvisited}"
    print("  -> Dynamic Scanner passed.")

def test_truck_emporium_tab():
    print("[TEST] Running Truck Emporium UI Mount Test...")
    root = tk.Tk()
    save_path_var = tk.StringVar(value="dummy_path.cfg")
    
    # Mount Tab
    frame = se.create_truck_emporium_tab(root, save_path_var, None)
    
    # Assertion 1: Ensure frame is packed (it will only report None inside this headless test if it wasn't packed by 'pack()')
    assert frame.pack_info() is not None, "Truck Emporium frame was not packed."
    
    # Assertion 2: Ensure database is populated in the Tkinter TreeView
    tree = None
    for child in frame.winfo_children():
        if isinstance(child, tk.ttk.Treeview) or child.winfo_class() == 'Treeview':
            tree = child
            break
            
    assert tree is not None, "Failed to locate Treeview inside Truck Emporium tab."
    children = tree.get_children()
    assert len(children) > 0, "Truck Emporium database failed to populate the Treeview!"
    print(f"  -> Truck Emporium UI loaded correctly with {len(children)} vehicles.")
    root.destroy()

def test_backup_logic():
    print("[TEST] Running Backup Return Truth Test...")
    temp_dir = tempfile.mkdtemp()
    dummy_save = os.path.join(temp_dir, "CompleteSave.cfg")
    open(dummy_save, 'w').write("test")
    
    try:
        # We simulate the UI checkboxes returning False
        se.make_backup_var = tk.BooleanVar()
        se.make_backup_var.set(True) # Ensure backup var is checked
        se.full_backup_var = tk.BooleanVar()
        se.full_backup_var.set(False) 
        
        # Test 1: Invalid Path (should return True to avoid blocking)
        res1 = se.make_backup_if_enabled("C:/invalid_path_123.cfg")
        assert res1 is True, f"Invalid path backup failed to return True. Got {res1}"
        
        # Test 2: Single Valid File (Force=True)
        res2 = se.make_backup_if_enabled(dummy_save, force=True)
        assert res2 is True, f"Force backup failed to return True. Got {res2}"
        
        print("  -> Backup UI return states passed.")
    finally:
        shutil.rmtree(temp_dir)

if __name__ == "__main__":
    try:
        # Mock the UI status update
        se.set_app_status = lambda msg, **kwargs: print(f"UI Status: {msg}")
        
        test_dynamic_scanner()
        test_truck_emporium_tab()
        test_backup_logic()
        print("\n=== ALL VALIDATION TESTS PASSED SUCCESSFULLY ===")
    except AssertionError as e:
        print(f"\n[!] VALIDATION FAILED: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"\n[!] UNEXPECTED ERROR: {e}")
        sys.exit(1)
