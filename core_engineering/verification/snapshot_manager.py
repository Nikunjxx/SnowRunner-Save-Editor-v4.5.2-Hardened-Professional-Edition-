# [PH4-VER-001] Snapshot Manager & Diff Engine (HARDENED)
import copy
import json
import fnmatch
from typing import Any, Dict, List, Tuple

class SnapshotManager:
    """
    State Capture Architecture for deep system observability.
    Enables precise, deterministic diffing between system states.
    [GAP-1] DIFF SCOPE VALIDATION (UNBREAKABLE).
    """
    
    @staticmethod
    def take_snapshot(state: Dict[str, Any]) -> Dict[str, Any]:
        """Captures a deep copy of the absolute state."""
        return copy.deepcopy(state)

    @staticmethod
    def diff(before: Dict[str, Any], after: Dict[str, Any]) -> Dict[str, Any]:
        """Performs a deep structural diff."""
        results = []

        def _compare(path: str, a: Any, b: Any):
            # [PH4-PERF-002] Identity-Based Fast Path.
            # If a is b, they are the same reference in memory. 
            # Skipping the entire branch.
            if a is b: 
                 return
            
            if type(a) != type(b):
                results.append({"type": "TYPE_MISMATCH", "path": path, "before": type(a).__name__, "after": type(b).__name__})
                return

            if isinstance(a, dict):
                keys_a, keys_b = set(a.keys()), set(b.keys())
                for k in sorted(keys_a.union(keys_b)):
                    new_path = f"{path}.{k}" if path else k
                    _compare(new_path, a.get(k), b.get(k))

            elif isinstance(a, list):
                if len(a) != len(b):
                    results.append({"type": "LIST_LENGTH_MISMATCH", "path": path, "before": len(a), "after": len(b)})
                
                max_len = max(len(a), len(b))
                for i in range(max_len):
                    new_path = f"{path}[{i}]"
                    _compare(new_path, a[i] if i < len(a) else None, b[i] if i < len(b) else None)

            else:
                if a != b:
                    results.append({"type": "VALUE_MISMATCH", "path": path, "before": a, "after": b})

        _compare("", before, after)
        return {"diff_count": len(results), "diffs": results}

    def validate_diff_scope(self, diff_result: Dict[str, Any], allowed_patterns: List[str]) -> Tuple[bool, List[str]]:
        """
        [GAP-1] Absolute Boundary Enforcement.
        Ensures that every detected diff matches at least one allowed pattern.
        Example patterns: 'derived.player.money', 'trucks.*.isUnlocked'
        """
        violations = []
        for diff in diff_result.get("diffs", []):
            path = diff["path"]
            matched = False
            for pattern in allowed_patterns:
                if fnmatch.fnmatch(path, pattern):
                    matched = True
                    break
            
            if not matched:
                violations.append(f"DIFF_BOUNDARY_VIOLATION: Path '{path}' changed unexpectedly. Not in allowed set {allowed_patterns}.")
                
        return len(violations) == 0, violations
