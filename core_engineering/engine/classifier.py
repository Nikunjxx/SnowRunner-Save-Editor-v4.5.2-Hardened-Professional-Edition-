import re
import yaml
import logging
from enum import Enum
from typing import Dict, List, Any, Optional

logger = logging.getLogger("InterpretationEngine")

class MismatchType(Enum):
    STRUCTURAL_OFFSET = "STRUCTURAL_OFFSET"
    TYPE_MISMATCH = "TYPE_MISMATCH"
    EXPECTED_DELTA = "EXPECTED_DELTA"
    NOISE = "NOISE"
    TRUE_MISMATCH = "TRUE_MISMATCH"
    UNKNOWN = "UNKNOWN"

class Severity(Enum):
    CRITICAL = "CRITICAL"
    WARNING = "WARNING"
    INFO = "INFO"

class ProgressionRules:
    """[PH2-RUL-004] Core logic for progression-based semantic interpretation."""
    
    _rules: Dict[str, str] = {}
    _initialized = False

    @classmethod
    def _initialize(cls):
        if cls._initialized:
            return
        try:
            # [PH2-RUL-006] Absolute Path Resolution
            import os
            engine_dir = os.path.dirname(os.path.abspath(__file__))
            rules_path = os.path.join(engine_dir, "rules.yaml")
            with open(rules_path, "r") as f:
                rules = yaml.safe_load(f)
                cls._rules = rules.get("progression", {})
            cls._initialized = True
        except Exception as e:
            logger.error(f"PROGRESSION_RULES_INIT_FAIL: {str(e)}")
            cls._rules = {}

    @classmethod
    def get_rule(cls, path: str) -> Optional[str]:
        cls._initialize()
        for pattern, rule in cls._rules.items():
            # [PH2-RUL-005] Hybrid Regex for SnowRunner Paths (Dots + Brackets)
            # Escape literal dots, convert * to global wildcard
            # Standard dots in the pattern can match either a dot or a bracket start
            regex = "^" + pattern.replace(".", r"[\.\[]").replace("*", ".*") + "$"
            if re.match(regex, path.replace("]", "")): # Strip closing bracket for simpler regex
                return rule
        return None

    @staticmethod
    def state_order(value) -> int:
        order = {
            "LOCKED": 0,
            "AVAILABLE": 1,
            "IN_PROGRESS": 2,
            "COMPLETED": 3
        }
        return order.get(str(value).upper(), -1)

    @classmethod
    def validate_progression(cls, path: str, old: Any, new: Any, ctx: Optional[dict] = None) -> bool:
        """[PH2-VAL-001] Behavioral validation vs Interpretation."""
        ctx = ctx or {}
        rule = cls.get_rule(path)
        if not rule:
            return False

        try:
            if rule == "MONOTONIC_INCREASE":
                return float(new) >= float(old)

            if rule == "TYPE_SAFE_VARIATION":
                # [PH2-RUL-007] Strict Type-Safe Variation
                # Allow None -> type, but block cross-type shifts (e.g., int -> str)
                if old is None:
                    return True
                if type(old) != type(new):
                    # Handle int vs float as same family if necessary, otherwise strict
                    if isinstance(old, (int, float)) and isinstance(new, (int, float)):
                        return True
                    return False
                return True

            if rule == "SET_GROWTH":
                if not isinstance(old, list) or not isinstance(new, list):
                    return False
                return set(old).issubset(set(new))

            if rule == "BOOLEAN_FLIP_TRUE":
                return (old is False and new is True)

            if rule == "REVERSIBLE_BOOLEAN":
                # [PH2-RUL-009] Scoped Reversal (Watchtowers/Fog only)
                return isinstance(old, bool) and isinstance(new, bool)

            if rule == "SESSION_SCOPED":
                # [PH2-RUL-010] Zero-Trust Cross-Session Guard
                # Only valid if Slot IDs differ (Cross-Save Audit)
                return ctx.get("is_cross_session") and type(old) == type(new)

            if rule == "CONDITIONAL_STATE":
                # [PH2-RUL-011] Reset-Aware Monotonicity
                is_ordered = cls.state_order(new) >= cls.state_order(old)
                is_reset = (path.startswith("CompleteSave.SslValue.tutorialStates") or 
                            path.startswith("CompleteSave.SslValue.contracts")) and ctx.get("new_game_flag")
                return is_ordered or is_reset

            if rule == "CONDITIONAL_LOCK":
                # [PH2-RUL-013] Identity-Ambiguity Resolution
                # Valid for ordered lists where positional index != physical identity
                return (isinstance(old, bool) and isinstance(new, bool) and (
                    ctx.get("is_cross_session") or 
                    ctx.get("garage_reset") or 
                    ctx.get("dlc_change")
                ))

            if rule == "POSITIONAL_DELTA":
                return True

            if rule == "STRUCTURAL_PRESENCE":
                # [PH2-RUL-012] Logical Existence Variance
                # Valid for nested structural leaves (scalar or collection)
                # transitioning to/from None.
                return True

        except Exception:
            return False

        return False

class DiffClassifier:
    """[PH2-CORE-003] Deterministic semantic classifier for Phase 2.4."""

    SEVERITY_MAP = {
        MismatchType.TYPE_MISMATCH: Severity.CRITICAL,
        MismatchType.STRUCTURAL_OFFSET: Severity.CRITICAL,
        MismatchType.TRUE_MISMATCH: Severity.CRITICAL,
        MismatchType.UNKNOWN: Severity.WARNING,
        MismatchType.EXPECTED_DELTA: Severity.INFO,
        MismatchType.NOISE: Severity.INFO
    }

    @staticmethod
    def get_severity(m_type: MismatchType) -> Severity:
        return DiffClassifier.SEVERITY_MAP.get(m_type, Severity.CRITICAL)
