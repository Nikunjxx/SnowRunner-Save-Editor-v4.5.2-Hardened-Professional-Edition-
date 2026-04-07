import difflib
from typing import List, Dict, Any

def suggest_mappings(missing_paths: List[str], ctx_state: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    [PH2-LRN-004] Fuzzy-matching for DERIVED_MAP candidates.
    Bridges the gap between raw save paths and logical derived keys.
    """
    suggestions = []
    
    # We flatten the context keys for fuzzy matching
    # (Simplified for now, will be upgraded with deeper similarity in Ph3)
    known_keys = list(ctx_state.keys())
    
    for path in missing_paths:
        # Extract the leaf key for fuzzy matching
        parts = path.split(".")
        leaf = parts[-1]
        
        # [PH2-LRN-005] Using difflib for baseline similarity
        matches = difflib.get_close_matches(leaf, known_keys, n=1, cutoff=0.6)
        
        if matches:
            suggestions.append({
                "raw_path": path,
                "derived_candidate": matches[0],
                "confidence": 0.6,
                "reason": f"Fuzzy match between {leaf} and {matches[0]}."
            })
            
    return suggestions
