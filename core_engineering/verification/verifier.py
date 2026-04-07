# [PH4-VER-005] Master Verifier (Orchestrator - FIXED)
from core_engineering.verification.test_cases import TEST_CASES
from core_engineering.verification.test_runner import TestRunner
from typing import Any, Dict, List

class Verifier:
    """
    Absolute Governance Orchestrator for Verification.
    Runs full test matrices and invariant audits.
    """
    
    def __init__(self, maprunner, validator):
        # CORRECT INJECTION [PH4-VER-FIX]
        self.runner = TestRunner(maprunner, validator)
        
    def run_all(self, base_state: Dict[str, Any]) -> List[Dict[str, Any]]:
        """ Executes the entire Verification Matrix. """
        results = []
        print(f"PIPELINE: Initiating Global Verification with {len(TEST_CASES)} cases.")
        
        for case in TEST_CASES:
            if "sequence" in case:
                result = self.runner.run_sequence(base_state, case)
            else:
                result = self.runner.run_test(base_state, case)
                
            results.append(result)
            status = result["status"]
            print(f"[{status}] Test: {result.get('test', 'UNKNOWN')}")
            
        return results

    def verify_regression(self, current_state: Dict[str, Any], golden_state: Dict[str, Any]):
        """ [PH4-VER-REG] Cross-referencing against architectural golden reference. """
        from verification.snapshot_manager import SnapshotManager
        diff = SnapshotManager.diff(golden_state, current_state)
        return diff
