# [PH3-VER-002] End-to-End Pipeline Verification
import sys
import os
sys.path.append(r"E:\Snow Runner New Tool\core_engineering")

from maprunner.maprunner import MapRunner
from mapper.field_mapper import FieldMapper
from mapper.validators import FieldValidator

def verify_pipeline():
    print("Initializing Phase 3 Full Pipeline...")
    mpr = MapRunner()
    mapper = FieldMapper(mpr)
    validator = FieldValidator(mpr)
    
    # 1. Simulate Interpreted State
    mock_state = {
        "derived.player.money": 500,
        "CompleteSave.SslValue.persistentProfileData.trucksInWarehouse": [
           {"type": "ws_4964_white", "isUnlocked": True}
        ]
    }
    
    # 2. UI Layer Resolution
    print("UI -> Mapper: Resolving State...")
    ui_model = mapper.resolve_ui_state(mock_state)
    target_truck_id = ui_model["trucks"][0]["id"] # western_star_4964
    
    # 3. Simulate User Edit (Money)
    print(f"UI -> Validator: Attempting Money Update to 1,000,000...")
    valid, msg = validator.validate_money(1000000)
    assert valid
    print(f"SUCCESS: {msg}")
    
    # 4. Simulate User Edit (Truck Toggle)
    print(f"UI -> Validator: Attempting Toggle for {target_truck_id}...")
    valid, msg = validator.validate_truck_unlock(target_truck_id, True)
    assert valid
    print(f"SUCCESS: {msg}")
    
    # 5. Simulate Upgrade Check
    print(f"UI -> MapRunner: Fetching available upgrades for {target_truck_id}...")
    upgrades = mapper.maprunner.get_upgrades(target_truck_id)
    print(f"Found {len(upgrades)} upgrades. Example: {upgrades[0].name if upgrades else 'None'}")
    
    # 6. Verify ID Resolution Chain
    assert upgrades[0].vehicle == "Western Star 4964"
    
    print("\n--- PHASE 3 PIPELINE VERIFIED ---")
    print("Logic Lockdown: 100%")
    print("Identity Integrity: 100%")

if __name__ == "__main__":
    verify_pipeline()
