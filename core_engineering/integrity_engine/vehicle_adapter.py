"""
SnowRunner Vehicle Mutation Adapter (Phase 6)
--------------------------------------------
Provides high-safety wrappers for vehicle mutations, routing them through
the IntegrityManager pipeline.
"""

import os
import re
import json
from integrity_engine.manager import IntegrityManager

def move_vehicle_safe(save_path, target_vehicle_id, new_coords, region_code=None, notify=True, integrity_manager=None):
    """Teleport vehicle using binary patching and bounding-box validation."""
    if integrity_manager is None:
        integrity_manager = IntegrityManager()

    if not region_code:
        match = re.search(r"((?:US|RU)_\d{2}_\d{2})", target_vehicle_id, re.I)
        region_code = match.group(1).lower() if match else None
        
    if not region_code:
        return False, f"Could not determine region for vehicle {target_vehicle_id}"

    payload = {
        "vehicle_id": target_vehicle_id,
        "coords": new_coords,
        "region": region_code
    }
    return integrity_manager.execute_feature("move_vehicle", save_path, payload)

def repair_vehicle_safe(save_path, vehicle_id, region, integrity_manager=None):
    """Repair and refuel vehicle using binary patching."""
    if integrity_manager is None:
        integrity_manager = IntegrityManager()

    payload = {
        "vehicle_id": vehicle_id,
        "region": region.lower()
    }
    return integrity_manager.execute_feature("repair_vehicle", save_path, payload)
