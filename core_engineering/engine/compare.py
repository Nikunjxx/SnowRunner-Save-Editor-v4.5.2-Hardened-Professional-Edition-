from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass

@dataclass
class RawDiffEntry:
    path: str
    old_value: Any
    new_value: Any
    is_structural: bool = False

class RawDiffResult:
    def __init__(self):
        self.diffs: List[RawDiffEntry] = []
        self.matched_count: int = 0
        self.total_count: int = 0

    def add_diff(self, entry: RawDiffEntry):
        self.diffs.append(entry)

class CompareEngine:
    """[PH2-CORE-001] Deep-path structural diff using canonical-aware iteration."""

    @staticmethod
    def diff(ctx_a: Any, ctx_b: Any) -> RawDiffResult:
        """[PH2-RULE-001] Canonical Comparison ONLY. Never raw."""
        result = RawDiffResult()
        
        # We compare the .state views (dictionaries) from FrozenContext
        stack: List[Tuple[str, Any, Any]] = [("", ctx_a.state, ctx_b.state)]
        
        while stack:
            path, val_a, val_b = stack.pop()
            result.total_count += 1
            
            # [PH2-ENG-001] Pure Structural Diff only.
            # Classification and Noise Filtering moved to InterpretationEngine.

            # Type Mismatch Check (Logical Diff)
            if type(val_a) != type(val_b):
                result.add_diff(RawDiffEntry(path, val_a, val_b, is_structural=True))
                continue

            # 3. Recursive Traversal
            if isinstance(val_a, dict):
                keys_a = set(val_a.keys())
                keys_b = set(val_b.keys())
                all_keys = sorted(list(keys_a.union(keys_b)))
                
                for k in all_keys:
                    new_path = f"{path}.{k}" if path else k
                    v_a = val_a.get(k)
                    v_b = val_b.get(k)
                    
                    if k not in keys_a:
                        # Missing in A
                        result.add_diff(RawDiffEntry(new_path, None, v_b, is_structural=True))
                    elif k not in keys_b:
                        # Missing in B
                        result.add_diff(RawDiffEntry(new_path, v_a, None, is_structural=True))
                    else:
                        stack.append((new_path, v_a, v_b))
                continue

            elif isinstance(val_a, list):
                # Canonicalized lists safely comparable by index
                len_a = len(val_a)
                len_b = len(val_b)
                max_len = max(len_a, len_b)
                
                for i in range(max_len):
                    new_path = f"{path}[{i}]"
                    v_a = val_a[i] if i < len_a else None
                    v_b = val_b[i] if i < len_b else None
                    
                    if i >= len_a:
                        result.add_diff(RawDiffEntry(new_path, None, v_b, is_structural=True))
                    elif i >= len_b:
                        result.add_diff(RawDiffEntry(new_path, v_a, None, is_structural=True))
                    else:
                        stack.append((new_path, v_a, v_b))
                continue

            # 4. Leaf Value Comparison
            if val_a != val_b:
                result.add_diff(RawDiffEntry(path, val_a, val_b))
            else:
                result.matched_count += 1
                
        return result
