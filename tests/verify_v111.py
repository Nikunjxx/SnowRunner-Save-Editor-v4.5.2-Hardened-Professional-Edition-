import os
import shutil
import uuid
import sys
from typing import Dict, Any

# Mock the SnowRunner environment
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from integrity_engine.manager import IntegrityManager
from integrity_engine.plugins.manager import PluginManager
from integrity_engine.plugins.dashboard_plugin import DashboardPlugin
from integrity_engine.plugins.map_unlock_plugin import MapUnlockPlugin
from integrity_engine.plugins.objectives_plugin import ObjectivesPlugin
from integrity_engine.plugins.save_compare_plugin import SaveComparePlugin
from integrity_engine.plugins.vehicle_inspector_plugin import VehicleInspectorPlugin
from integrity_engine.plugins.plugin_manager_plugin import PluginManagerPlugin

def setup_mock_folder(folder_path: str):
    """Creates a mock SnowRunner directory with mixed Steam/Epic artifacts."""
    if os.path.exists(folder_path):
        shutil.rmtree(folder_path)
    os.makedirs(folder_path)
    
    # 1. Main Progressive Save (Steam style)
    with open(os.path.join(folder_path, "CompleteSave.cfg"), "wb") as f:
        # Valid Header: AK\x05\x00
        f.write(b"\x41\x4b\x05\x00")
        import zlib
        f.write(zlib.compress(b'{"money": 1000, "rank": 1}'))
    
    # 2. Global Save
    with open(os.path.join(folder_path, "CommonSslSave.cfg"), "wb") as f:
        f.write(b"\x41\x4b\x05\x00")
        f.write(zlib.compress(b'{"global_stuff": "test"}'))
        
    # 3. World Markers (STS)
    with open(os.path.join(folder_path, "sts_level_us_01_01.cfg"), "wb") as f:
        f.write(b"\x41\x4b\x05\x00")
        f.write(zlib.compress(b'{"markers": []}'))
        
    # 4. Fog Discovery (Epic style header to test mixed)
    with open(os.path.join(folder_path, "fog_level_us_01_01.dat"), "wb") as f:
        # Epic Header: \xd3\xa6\x02\x00
        f.write(b"\xd3\xa6\x02\x00")
        f.write(zlib.compress(b'FOG_DATA_MOCK'))

def run_verification():
    print("=== SNOWRUNNER V111.00 VERIFICATION SUITE ===")
    
    # [v111.00] Initialize hidden root for plugins that use tk.Vars during registration
    import tkinter as tk
    root = tk.Tk()
    root.withdraw()
    
    mock_dir = os.path.abspath("./tests/mock_save")
    app_data = os.path.abspath("./tests/app_data")
    if not os.path.exists(app_data): os.makedirs(app_data)
    
    setup_mock_folder(mock_dir)
    
    # --- TEST 1: FOLDER HEURISTICS ---
    print("\n[T1] Testing Folder Loader Heuristics...")
    manager = IntegrityManager(mock_dir, app_data, remote2_path="./tests/remote2")
    ctx = manager.get_save_context()
    
    assert ctx["main"] == "CompleteSave.cfg", f"Main Save Failure: {ctx['main']}"
    assert ctx["global"] == "CommonSslSave.cfg", f"Global Save Failure: {ctx['global']}"
    assert "us_01_01" in ctx["sts"], f"STS Mapping Failure: {ctx['sts']}"
    assert "us_01_01" in ctx["fog"], f"Fog Mapping Failure: {ctx['fog']}"
    assert ctx["platform"] == "Steam", f"Platform Detection Failure: {ctx['platform']}"
    print(">>> PASS: Folder Heuristics Verified.")

    # --- TEST 2: TRANSACTION SUCCESS ---
    print("\n[T2] Testing Transaction Logic (Success Path)...")
    original_size = os.path.getsize(os.path.join(mock_dir, "CompleteSave.cfg"))
    
    with manager.transaction(whitelist=["CompleteSave.cfg"]) as tx_id:
        print(f"Executing Mutation in TX: {tx_id}")
        target_path = os.path.join(mock_dir, "CompleteSave.cfg")
        with open(target_path, "wb") as f:
            f.write(b"\x41\x4b\x05\x00")
            import zlib
            f.write(zlib.compress(b'{"money": 999999, "rank": 30}'))
            
    # Verify snapshot updated
    assert manager.session_state == "MODIFIED", "Session state should be MODIFIED after commit."
    print(">>> PASS: Transaction Committed Successfully.")

    # --- TEST 3: TRANSACTION ROLLBACK ---
    print("\n[T3] Testing Transaction Logic (Rollback Path)...")
    mtime_before = os.path.getmtime(os.path.join(mock_dir, "CompleteSave.cfg"))
    
    try:
        with manager.transaction(whitelist=["CompleteSave.cfg"]) as tx_id:
            print("Simulating Plugin Crash...")
            # Corrupt the file manually
            with open(os.path.join(mock_dir, "CompleteSave.cfg"), "wb") as f:
                f.write(b"CORRUPTED_GARBAGE")
            raise RuntimeError("CRITICAL_PLUGIN_FAILURE_SIM")
    except RuntimeError as e:
        print(f"Caught Expected Exception: {e}")
        
    # Verify rollback
    with open(os.path.join(mock_dir, "CompleteSave.cfg"), "rb") as f:
        header = f.read(4)
        assert header == b"\x41\x4b\x05\x00", f"Rollback failed: Magic header corrupt: {header}"
    print(">>> PASS: Transaction Rolled Back Correctly.")

    # --- TEST 4: PLUGIN REGISTRY ---
    print("\n[T4] Testing Plugin Discovery & Metadata...")
    plugin_manager = PluginManager(manager, {"set_app_status": lambda x, **k: print(f"UI_STATUS: {x}")})
    
    # Register core set
    plugin_manager.register_plugin(DashboardPlugin())
    plugin_manager.register_plugin(MapUnlockPlugin())
    plugin_manager.register_plugin(ObjectivesPlugin())
    plugin_manager.register_plugin(SaveComparePlugin())
    plugin_manager.register_plugin(VehicleInspectorPlugin())
    plugin_manager.register_plugin(PluginManagerPlugin(plugin_manager))
    
    plugins = plugin_manager.get_all_plugins()
    assert len(plugins) == 6, f"Plugin Registration Failure: {len(plugins)} found."
    
    # Verify PluginManager UI
    sys_plugins = plugin_manager.get_plugins_by_category("SYSTEM")
    assert any(p.id == "system_plugin_manager" for p in sys_plugins), "Plugin Manager UI not in SYSTEM category."
    
    # Verify Mutation Wrapping
    mu_plugin = plugin_manager.get_plugin("map_unlock")
    assert mu_plugin.plugin_type == "mutation", "MapUnlock should be a mutation plugin."
    
    print(">>> PASS: Plugin Discovery Verified.")
    
    print("\n=== VERIFICATION COMPLETE: V111.00 IS ARCHITECTURALLY STABLE ===")

if __name__ == "__main__":
    try:
        run_verification()
    except Exception as e:
        print(f"\n!!! VERIFICATION FAILED !!!\n{str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
