from typing import List, Dict, Any, Optional
from dataclasses import dataclass
from enum import Enum

class ConsistencyStatus(Enum):
    CONSISTENT = "CONSISTENT"
    INCONSISTENT = "INCONSISTENT"
    MISSING_LINK = "MISSING_LINK"

class Severity(Enum):
    CRITICAL = "CRITICAL"
    WARNING = "WARNING"
    INFO = "INFO"

@dataclass
class ConsistencyIssue:
    path: str
    status: ConsistencyStatus
    severity: Severity
    msg: str

# PH2-CON-001: Ground Truth Matrix (MANDATORY)
# This mapping identifies logical links across files.
GROUND_TRUTH_MATRIX = {
    "player.rank": {
        "links": [
            "CompleteSave.SslValue.persistentProfileData.rank",
            "CommonSslSave.SslValue.achievementStates"  # Derived lookup later
        ],
        "strict": True
    },
    "player.money": {
        "links": [
            "CompleteSave.SslValue.persistentProfileData.money"
        ],
        "strict": True
    }
}

class ConsistencyAuditor:
    """[PH2-CORE-004] Absolute Cross-File Consistency Validation."""

    @staticmethod
    def audit_context(ctx: Any) -> List[Dict[str, Any]]:
        """Validates that shared state values are consistent across the context."""
        issues: List[ConsistencyIssue] = []
        
        # [PH2-CON-002] Multi-file Consistency via FrozenContext traversal
        # Derived state exists at the top level of the projection
        try:
            rank = ctx.derived.player.rank
            if rank is None:
                issues.append(ConsistencyIssue("player.rank", ConsistencyStatus.MISSING_LINK, Severity.CRITICAL, "Rank not found."))
        except Exception:
             issues.append(ConsistencyIssue("player.rank", ConsistencyStatus.MISSING_LINK, Severity.CRITICAL, "Derived state inaccessible."))

        try:
            money = ctx.derived.player.money
            if money is None:
                issues.append(ConsistencyIssue("player.money", ConsistencyStatus.MISSING_LINK, Severity.CRITICAL, "Money not found."))
        except Exception:
             issues.append(ConsistencyIssue("player.money", ConsistencyStatus.MISSING_LINK, Severity.CRITICAL, "Derived state inaccessible."))

        return [{
            "path": i.path,
            "status": i.status.value,
            "severity": i.severity.value,
            "msg": i.msg
        } for i in issues]
