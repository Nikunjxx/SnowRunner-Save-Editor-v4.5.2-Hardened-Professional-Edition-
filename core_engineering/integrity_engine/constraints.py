"""
SnowRunner Constraint Engine (Phase 7)
-------------------------------------
Implements rule-based validation (Constraint-Driven) for save mutations.
Enforces physical and logical game limits before they reach the game.
"""

from typing import Dict, Any, List, Optional
import os
import re

# Reference Table: Typical Fuel Capacities (v110.40 baseline)
# This serves as the 'Constraint Model' for fuel validation.
TRUCK_CAPACITIES = {
    "truck_us_scout_chevrolet_ck1500": 80.0,
    "truck_ru_scout_khan_39_marshall": 40.0,
    "truck_ru_scout_tuz_420_tatarin": 300.0,
    "truck_us_offroad_ank_mk38": 200.0,
    "truck_ru_heavy_zikz_605r": 450.0,
    "truck_us_heavy_pacific_p12": 350.0,
    "truck_us_heavy_kolob_74760": 380.0,
    "truck_ru_heavy_azov_73210": 350.0,
    "truck_ru_heavy_tayga_6436": 330.0,
    "default": 200.0
}

# Quest-Safe Protection: Mission-Critical Cargo (v110.40)
# These items are blocked from manual spawning to prevent breaking mission triggers.
QUEST_CARGO_IDS = [
    "CargoPrototypeExplorationUnit",
    "CargoRadioactiveWaste",
    "CargoUnique",
    "CargoObjective",
    "CargoQuest"
]

class ConstraintReport:
    """
    Data model for constraint validation results.
    Tracks violations and overall validity.
    """
    def __init__(self):
        self.is_valid = True
        self.violations = []

    def add_violation(self, message: str):
        self.is_valid = False
        self.violations.append(message)

class ConstraintEngine:
    """
    Elite Level Validation: Domain-Separated Logic Enforcement.
    UI -> [ConstraintEngine] -> [IntegrityManager]
    """
    def __init__(self, target_folder: str = None):
        self.target_folder = target_folder

    def validate_mutation(self, feature: str, payload: Dict[str, Any]) -> ConstraintReport:
        """EntryPoint for all domain-aware logic validation."""
        report = ConstraintReport()
        
        # Domain Separation (v110.41)
        if "vehicle" in feature:
            self._validate_vehicle_domain(feature, payload, report)
        elif "trailer" in feature:
            self._validate_trailer_domain(feature, payload, report)
        elif "cargo" in feature:
            self._validate_cargo_domain(feature, payload, report)
        elif feature == "add_fuel":
             self._validate_vehicle_domain(feature, payload, report)
            
        return report

    # --- Domain 1: Vehicles ---
    def _validate_vehicle_domain(self, feature: str, payload: Dict[str, Any], report: ConstraintReport):
        if "move" in feature:
            self._validate_move_coords(payload, report)
        if "repair" in feature or "fuel" in feature:
            self._validate_repair_context(payload, report)
            self._validate_fuel_limits(payload, report)

    # --- Domain 2: Trailers ---
    def _validate_trailer_domain(self, feature: str, payload: Dict[str, Any], report: ConstraintReport):
        if "move" in feature:
            self._validate_move_coords(payload, report)
        if "repair" in feature:
             # Trailers also have region affinity
             self._validate_repair_context(payload, report)

    # --- Domain 3: Cargo (High Risk) ---
    def _validate_cargo_domain(self, feature: str, payload: Dict[str, Any], report: ConstraintReport):
        """Implements the 5 Strict Cargo Rules."""
        cargo_id = payload.get("cargo_id", "")
        vehicle_id = payload.get("vehicle_id", "")
        region = payload.get("region", "")
        op = payload.get("op", "add")

        if op != "add": return # Removals are inherently safe

        # Rule 1: Mission-Locked / Quest-Safe
        for blocked in QUEST_CARGO_IDS:
            if blocked.lower() in cargo_id.lower():
                report.add_violation(f"Quest Constraint: Cargo '{cargo_id}' is mission-critical and blocked.")

        # Rule 2: Carrier Validation
        if not vehicle_id:
            report.add_violation("Carrier Constraint: No target vehicle/trailer specified for cargo.")
        
        # Rule 3: Region Consistency
        if region and vehicle_id:
            match = re.search(r"((?:US|RU)_\d{2}_\d{2})", vehicle_id, re.I)
            if match:
                v_region = match.group(1).lower()
                if v_region != region.lower():
                    report.add_violation(f"Region Constraint: Cargo carrier '{vehicle_id}' is in {v_region}, but target is {region}.")

        # Rule 4: Capacity & Uniqueness Warnings
        # (Note: deep STS validation is handled in the mutator layer for efficiency, 
        # but logical blocks are registered here).
        if not cargo_id:
             report.add_violation("Cargo Constraint: No cargo type specified.")

    # --- Internal Utilities ---
    def _validate_move_coords(self, payload: Dict[str, Any], report: ConstraintReport):
        """Rule: Bounding Box (2048) + Terrain Safety."""
        coords = payload.get("coords") or [payload.get("x", 0), payload.get("z", 0)]
        
        x, z = float(coords[0]), float(coords[1])
        LIMIT = 2048.0 
        
        if abs(x) > LIMIT or abs(z) > LIMIT:
            report.add_violation(f"Physical Constraint: ({x}, {z}) is outside map boundaries (Â±{LIMIT}).")

        y = payload.get("y", 1.0)
        if y < -10:
            report.add_violation(f"Terrain Constraint: Altitude {y} is invalid (Collision/Void Danger).")

    def _validate_repair_context(self, payload: Dict[str, Any], report: ConstraintReport):
        """Rule: Region Affinity."""
        target_id = payload.get("vehicle_id") or payload.get("trailer_id", "")
        region = payload.get("region", "")
        
        if region and target_id:
            match = re.search(r"((?:US|RU)_\d{2}_\d{2})", target_id, re.I)
            if match:
                v_region = match.group(1).lower()
                if v_region != region.lower():
                    report.add_violation(f"Region Affinity: '{target_id}' belongs to {v_region}, not {region}.")

    def _validate_fuel_limits(self, payload: Dict[str, Any], report: ConstraintReport):
        """Rule: Fuel Capacity (No Overfilling)."""
        vehicle_id = payload.get("vehicle_id", "")
        fuel = payload.get("fuel", 999.0) 
        
        if isinstance(fuel, (int, float)) and fuel > 0 and fuel != 999.0:
            v_type = self._extract_truck_type(vehicle_id)
            capacity = TRUCK_CAPACITIES.get(v_type, TRUCK_CAPACITIES["default"])
            if fuel > capacity * 1.5:
                report.add_violation(f"Capacity Constraint: {fuel}L exceeds vehicle capacity limit ({capacity}L).")

    def _extract_truck_type(self, vehicle_id: str) -> str:
        parts = vehicle_id.split("_")
        if len(parts) > 5:
            return "_".join(parts[:5])
        return vehicle_id
