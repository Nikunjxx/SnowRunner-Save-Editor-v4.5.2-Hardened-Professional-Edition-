# [PH4-VER-003] Testing Execution Engine (HARDENED)
from core_engineering.verification.snapshot_manager import SnapshotManager
from core_engineering.verification.invariants import InvariantChecker
from core_engineering.engine.mutation_engine import MutationEngine
from typing import Any, Dict, List, Optional
import copy

class TestRunner:
    """
    Core executor for Mutation Verification (Hardened).
    [GAP-3] Pipeline Stage Assertions.
    [GAP-5] Absolute Test Isolation.
    """
    
    def __init__(self, maprunner, validator):
        self.maprunner = maprunner
        self.validator = validator
        self.snapshot_mgr = SnapshotManager()

    def run_test(self, base_state: Dict[str, Any], test_case: Dict[str, Any]) -> Dict[str, Any]:
        """ Executes a single mutation test under isolation. """
        
        # [GAP-5] FRESH ENGINE PER TEST
        engine = MutationEngine(self.maprunner, self.validator)
        engine.set_state(base_state)
        
        # 1. State Normalization
        before_state = self.snapshot_mgr.take_snapshot(engine.state)
        test_name = test_case.get("name", "Unnamed Test")
        expect_failure = test_case.get("expect_failure", False)
        
        try:
            # 2. Mutation Pipeline execution
            result = engine.apply_change(
                test_case["field"],
                test_case["value"],
                test_case.get("context", {})
            )
            
            # [GAP-3] Stage Assertions
            if result.success:
                if expect_failure:
                    return {"test": test_name, "status": "FAIL", "reason": "Illegal mutation passed validator unexpectedly."}
            else:
                if not expect_failure:
                    return {"test": test_name, "status": "FAIL", "reason": f"Validator Stage Rejected: {result.message}"}
                return {"test": test_name, "status": "PASS", "reason": "Expected Rejection Captured."}

            # 3. Post-Mutation Guard [PH4-VER-INF]
            after_state = self.snapshot_mgr.take_snapshot(engine.state)
            
            # 4. Invariant Checking (GAP-2)
            inv_errors = InvariantChecker.validate(after_state)
            if inv_errors:
                return {"test": test_name, "status": "CRITICAL_FAIL", "reason": "Invariant Violation", "errors": inv_errors}
            
            # 5. Diff-Scope Enforcement (GAP-1)
            diff_result = self.snapshot_mgr.diff(before_state, after_state)
            allowed_paths = test_case.get("allowed_diff_paths", [test_case["field"]])
            
            # Add implicit structural paths to allowed (e.g. money -> derived.player.money)
            # This is handled by defining the correct paths in test_cases.py
            
            valid_diff, violations = self.snapshot_mgr.validate_diff_scope(diff_result, allowed_paths)
            if not valid_diff:
                return {"test": test_name, "status": "CRITICAL_FAIL", "reason": "Diff Boundary Violation", "errors": violations}
            
            return {
                "test": test_name,
                "status": "PASS",
                "diff": diff_result
            }

        except Exception as e:
            if expect_failure:
                return {"test": test_name, "status": "PASS", "reason": "Expected Exception Captured."}
            return {"test": test_name, "status": "FAIL", "reason": f"System Crash: {str(e)}"}

    def run_sequence(self, base_state: Dict[str, Any], test_case: Dict[str, Any]) -> Dict[str, Any]:
        """ Runs a multi-step mutation chain under isolation. """
        engine = MutationEngine(self.maprunner, self.validator)
        engine.set_state(base_state)
        
        steps = test_case.get("sequence", [])
        for i, step in enumerate(steps):
            # Run individual steps manually against the engine for sequential state updates
            result = self.run_test(engine.state, {
                "name": f"{test_case['name']} (Step {i})",
                "field": step["field"],
                "value": step["value"],
                "context": step.get("context", {}),
                "allowed_diff_paths": test_case.get("allowed_diff_paths", [step["field"]]),
                "expect_failure": test_case.get("expect_failure", False)
            })
            
            if result["status"] != "PASS":
                return result
                
        return {"test": test_case["name"], "status": "PASS", "reason": "Sequence Complete"}
