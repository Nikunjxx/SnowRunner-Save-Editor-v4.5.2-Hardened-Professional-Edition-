import logging
from enum import Enum, auto

logger = logging.getLogger("ConflictResolution")

class Severity(Enum):
    INFO = auto()
    WARNING = auto()
    CRITICAL = auto()
    STRICT = auto()

class Verdict(Enum):
    HEALTHY = auto()
    PROCEED_WITH_CAUTION = auto()
    FATAL_ABORT = auto()

# [PH1-RUL-001] Supreme Resolution Matrix
# Truth Table for Validation vs. Intent:
MATRIX = {
    Severity.STRICT: Verdict.FATAL_ABORT,   # Strict validation ALWAYS aborts
    Severity.CRITICAL: Verdict.FATAL_ABORT, # Critical failure ALWAYS aborts
    Severity.WARNING: {
        Severity.STRICT: Verdict.FATAL_ABORT, # If intent is strict, warnings abort
        Severity.WARNING: Verdict.PROCEED_WITH_CAUTION,
        Severity.INFO: Verdict.PROCEED_WITH_CAUTION,
    },
    Severity.INFO: Verdict.HEALTHY # Info-only validation proceeds
}

def resolve_verdict(validation_severity: Severity, intent_severity: Severity) -> Verdict:
    """
    Implements the definitive Conflict Resolution Rule.
    Determines if the hydration/transaction should proceed.
    """
    rule = MATRIX.get(validation_severity)
    
    if isinstance(rule, Verdict):
        return rule
        
    return rule.get(intent_severity, Verdict.FATAL_ABORT)
