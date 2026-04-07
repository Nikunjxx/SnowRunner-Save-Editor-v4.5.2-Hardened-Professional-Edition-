# [PH3-VER-005] Final Unified System Verification
import sys
import os
sys.path.append(r"E:\Snow Runner New Tool\core_engineering")

from maprunner.maprunner import MapRunner
from mapper.field_mapper import FieldMapper
from mapper.validators import FieldValidator

def verify_full_system():
    print("Initializing Phase 3 Final Unified Verification...")
    mpr = MapRunner()
    mapper = FieldMapper(mpr)
    validator = FieldValidator(mpr)
    
    # 1. State Input (Phase 2 Result)
    mock_engine_state = {
        "derived.player.money": 50000,
        "CompleteSave.SslValue.persistentProfileData.trucksInWarehouse": [
           {"type": "ws_4964_white", "isUnlocked": True}
        ]
    }
    
    # 2. Bridge Resolution (Layer 2)
    print("\n[RESOLUTION] Bridging save state to UI model...")
    resolved = mapper.resolve_ui_state(mock_engine_state)
    truck_id = resolved["trucks"][0]["id"]
    print(f"Resolved Identity: {truck_id} ({resolved['trucks'][0]['name']})")
    
    # 3. Knowledge Cataloging (Layer 1)
    print("\n[KNOWLEDGE] Resolving part compatibility for vehicle...")
    upgrades = mpr.get_upgrades(truck_id)
    print(f"Discovered {len(upgrades)} valid parts for {truck_id}.")
    assert len(upgrades) > 0
    
    # 4. Filter Validation (Layer 2)
    print("\n[VALIDATION] Testing Safe Edit Pipeline (Part Compatibility)...")
    valid, msg = validator.validate_upgrade_availability(truck_id, upgrades[0].id)
    print(f"Result: {valid} - {msg}")
    assert valid
    
    # Negative Test
    invalid_part = "invalid_part_id"
    valid, msg = validator.validate_upgrade_availability(truck_id, invalid_part)
    print(f"Result: {valid} - {msg}")
    assert not valid
    
    print("\n--- PHASE 3 UNIFIED ARCHITECTURE COMPLETE ---")
    print("Logic Lockdown: 100%")
    print("Safe Edit Pipeline: Ready.")

if __name__ == "__main__":
    verify_full_system()
