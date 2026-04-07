from collections import defaultdict
from typing import List, Dict, Any, Tuple

class PatternMiner:
    """[PH2-LRN-001] Data-driven rule discovery via delta distribution analysis."""
    
    def __init__(self):
        # path -> list of (old, new) pairs
        self.path_stats = defaultdict(list)

    def ingest(self, diff_entries: List[Dict[str, Any]]):
        """Accumulates diff entries for cross-run analysis."""
        for entry in diff_entries:
            path = entry["path"]
            old = entry["old"]
            new = entry["new"]
            self.path_stats[path].append((old, new))

    def _has_variation(self, values: List[Tuple[Any, Any]]) -> bool:
        """[PH2-LRN-002] Prevents false 'constant' rules for non-variant data."""
        # Check if the 'new' value has actually changed across samples
        new_vals = [v[1] for v in values]
        return len(set(new_vals)) > 1

    def analyze(self) -> Dict[str, Any]:
        """Identifies repeatable behaviors and transition patterns."""
        patterns = {}

        for path, values in self.path_stats.items():
            if not self._has_variation(values):
                # We skip paths that don't vary across samples to avoid noise
                continue

            deltas = []
            for old, new in values:
                try:
                    # Attempt numeric delta calculation
                    delta = float(new) - float(old)
                    deltas.append(delta)
                except Exception:
                    continue

            if not deltas:
                continue

            increasing = all(d >= 0 for d in deltas)
            decreasing = all(d <= 0 for d in deltas)
            constant = all(d == 0 for d in deltas)

            patterns[path] = {
                "samples": len(values),
                "always_increasing": increasing,
                "always_decreasing": decreasing,
                "always_constant": constant,
                "avg_delta": sum(deltas) / len(deltas) if deltas else 0
            }

        return patterns
