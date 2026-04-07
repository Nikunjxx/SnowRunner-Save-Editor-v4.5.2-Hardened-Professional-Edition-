# [PH3-VER-001] Layer 2 Bridge Verification
import sys
import os
sys.path.append(r"E:\Snow Runner New Tool\core_engineering")

from maprunner.maprunner import MapRunner
from mapper.field_mapper import FieldMapper

def verify_bridge():
    print("Initializing Layer 1 (MapRunner)...")
    mpr = MapRunner()
    
    print("Initializing Layer 2 (FieldMapper)...")
    mapper = FieldMapper(mpr)
    
    # Mock Interpreted State (Phase 2 Output)
    mock_state = {
        "derived.player.money": 599000,
        "CompleteSave.SslValue.persistentProfileData.trucksInWarehouse": [
            {"type": "ws_4964_white", "isUnlocked": True},
            {"type": "chevrolet_ck1500", "isUnlocked": True}
        ]
    }
    
    print("Executing Field Resolution...")
    ui_state = mapper.resolve_ui_state(mock_state)
    
    print("\n--- RESOLVED UI MODEL ---")
    print(f"Money: {ui_state['player']['money']}")
    print("Trucks in Warehouse:")
    for truck in ui_state['trucks']:
        print(f" - [{truck['id']}] {truck['name']} (Unlocked: {truck['is_unlocked']})")
    
    # Assert ID Normalization
    assert ui_state['trucks'][0]['id'] == 'western_star_4964'
    print("\nVERIFICATION PASSED: Identity-Based Resolution Successful.")

if __name__ == "__main__":
    verify_bridge()
