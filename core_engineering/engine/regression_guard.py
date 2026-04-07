import json
import os
import logging
from typing import Dict, Any

logger = logging.getLogger("InterpretationEngine")

class RegressionGuard:
    """[PH2-GOV-003] Safety latch to prevent interpretation regressions."""
    
    BASELINE_FILE = "baseline_metrics.json"

    @classmethod
    def check_regression(cls, current_metrics: Dict[str, Any]) -> str:
        """
        Compares current mission metrics against the stored baseline.
        Returns "PASS" or a failure reason.
        """
        if not os.path.exists(cls.BASELINE_FILE):
            cls._save_baseline(current_metrics)
            return "PASS (NEW_BASELINE)"

        try:
            with open(cls.BASELINE_FILE, "r") as f:
                baseline = json.load(f)
            
            # [PH2-GOV-004] Core Safety Latch: Confidence must not drop
            if current_metrics["confidence"] < baseline["confidence"]:
                return f"FAIL_CONFIDENCE_DROP: {current_metrics['confidence']:.4f} < {baseline['confidence']:.4f}"
            
            # [PH2-GOV-005] Critical Saftey Latch: TRUE_MISMATCH must not increase
            if current_metrics["true_mismatch"] > baseline["true_mismatch"]:
                return f"FAIL_MISMATCH_INCREASE: {current_metrics['true_mismatch']} > {baseline['true_mismatch']}"
                
            # If current is equal or better, update the baseline
            cls._save_baseline(current_metrics)
            return "PASS"
            
        except Exception as e:
            logger.error(f"REGRESSION_GUARD_ERROR: {str(e)}")
            return "ERROR_CHECK_FAILED"

    @classmethod
    def _save_baseline(cls, metrics: Dict[str, Any]):
        """Persists the latest high-water mark for metrics."""
        try:
            with open(cls.BASELINE_FILE, "w") as f:
                json.dump(metrics, f, indent=4)
        except Exception as e:
            logger.error(f"BASELINE_SAVE_FAIL: {str(e)}")
