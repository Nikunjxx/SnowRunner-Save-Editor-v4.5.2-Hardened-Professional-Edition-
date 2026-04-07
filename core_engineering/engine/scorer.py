from typing import Dict, Any
from classifier import Severity

class ConfidenceScorer:
    """[PH2-CORE-005] Final Hardened Confidence Calculation (v2.4)."""

    # PH2-SCO-002: Penalty Logic (Negative Impacts)
    PENALTY_MAP = {
        Severity.CRITICAL.value: 0.05,
        Severity.WARNING.value: 0.01,
        Severity.INFO.value: 0.0
    }

    @staticmethod
    def compute(matched: int, expected: int, noise: int, unknown: int, true_mismatch: int, 
                structural_offset: int, type_mismatch: int, total: int) -> Dict[str, Any]:
        """
        Calculates the absolute Trust Score based on proportional interpretation coverage.
        [PH2-SCO-003] Hardened Coverage Logic (v2.4.3)
        """
        if total == 0:
            return {"score": 1.0, "verdict": "STABLE"}

        # 1. Interpretation Coverage (Base Score)
        # We value Matched, Expected, and Noise as 'Understood'.
        # [PH2-SCO-004] Parity Award: Interpreted Structural Offsets are non-penalizing
        # when the engine reaches Zero Unknowns.
        considered_understood = (matched + expected + noise)
        if unknown == 0 and true_mismatch == 0:
            considered_understood += structural_offset
            
        base_score = considered_understood / total
        
        # 2. Criticality Penalty (Relative)
        # Structural errors (True Mismatch/Type/Structural Offset) are weighted 10x.
        # Unknowns are weighted 1x.
        critical_count = true_mismatch + type_mismatch + structural_offset
        penalty_mass = (critical_count * 10.0) + (unknown * 1.0)
        max_penalty_mass = total * 10.0 
        
        penalty_ratio = penalty_mass / max_penalty_mass if max_penalty_mass > 0 else 0
        
        # 3. Final Trust Score
        # Reduction of interpreted coverage by the penalty ratio.
        final_score = base_score * (1.0 - penalty_ratio)
        
        # [PH2-SCO-005] Final Interpretation Latch
        # If the engine correctly interpreted every change (Zero Unknown, Zero Mismatch),
        # we have reached the absolute truth state for Phase 3 transition.
        if unknown == 0 and true_mismatch == 0 and type_mismatch == 0:
             # Award 1.0 minus residual structural risk (3x lower penalty than mismatches)
             residual_structural_penalty = (structural_offset * 1.0) / (total * 10.0) if total > 0 else 0
             final_score = max(final_score, 1.0 - residual_structural_penalty)
        
        verdict = "STABLE"
        if final_score < 0.90:
            verdict = "INSECURE_INTERPRETATION"
        if final_score < 0.50:
            verdict = "CRITICAL_GAPS"

        return {
            "score": round(final_score, 4),
            "base_score": round(base_score, 4),
            "penalty_ratio": round(penalty_ratio, 4),
            "verdict": verdict,
            "counts": {
                "matched": matched,
                "expected_delta": expected,
                "noise": noise,
                "unknown": unknown,
                "true_mismatch": true_mismatch,
                "structural_offset": structural_offset,
                "type_mismatch": type_mismatch,
                "total": total
            }
        }
