# [PH4-VER-007] Regression Guard (Golden State)
import json
import os
from verification.snapshot_manager import SnapshotManager

class RegressionGuard:
    """
    Ensures absolute consistency vs known-good architectural snapshots.
    """
    
    def __init__(self, golden_dir="core_engineering/verification/golden"):
        self.golden_dir = golden_dir
        if not os.path.exists(self.golden_dir):
            os.makedirs(self.golden_dir)

    def load_golden(self, name: str) -> dict:
        path = os.path.join(self.golden_dir, f"{name}.json")
        if not os.path.exists(path):
            return {}
        with open(path, "r") as f:
            return json.load(f)

    def compare(self, current_state: dict, golden_name: str) -> dict:
        """
        Compares the current system state against a golden snapshot.
        """
        golden = self.load_golden(golden_name)
        if not golden:
            return {"error": f"Golden state '{golden_name}' not found."}
            
        diff = SnapshotManager.diff(golden, current_state)
        return diff
