from typing import List, Dict, Any

def suggest_progression_rules(patterns: Dict[str, Any], threshold: int = 3) -> List[Dict[str, Any]]:
    """
    [PH2-LRN-003] Proposes classification rules with confidence weighting.
    Only proposes rules with enough sample diversity (SAMPLES >= threshold).
    """
    suggestions = []

    for path, meta in patterns.items():
        if meta["samples"] < threshold:
            continue

        # Rule 1: Monotonic Increase
        if meta["always_increasing"] and not meta["always_constant"]:
            suggestions.append({
                "path": path,
                "rule": "MONOTONIC_INCREASE",
                "confidence": 0.9,
                "reason": f"Always increases over {meta['samples']} samples."
            })

        # Rule 2: Constant Value (Noise Candidate)
        elif meta["always_constant"]:
            suggestions.append({
                "path": path,
                "rule": "NOISE_CANDIDATE",
                "confidence": 0.7,
                "reason": f"Always constant over {meta['samples']} samples."
            })
            
        # Rule 3: Positional Change
        elif "waypoints" in path:
             suggestions.append({
                "path": path,
                "rule": "POSITIONAL_DELTA",
                "confidence": 0.8,
                "reason": f"Waypoints variation detected."
            })

    return suggestions
