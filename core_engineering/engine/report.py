import logging
from typing import List, Dict, Any, Optional
from rules import Severity, Verdict, resolve_verdict

logger = logging.getLogger("ReportingEngine")

class ReportEntry:
    def __init__(self, step_id: str, severity: Severity, msg: str, time_ms: float = 0.0):
        self.step_id = step_id
        self.severity = severity
        self.msg = msg
        self.time_ms = time_ms

class HydrationReport:
    """
    Diagnostic Report with Verdict Aggregation Logic.
    Mandatory Feature: Hash Visibility for Audit.
    """
    def __init__(self, slot_id: int):
        self.slot_id = slot_id
        self.ctx_hash: str = "PENDING"
        self.engine_version: str = "1.3"
        self.schema_version: str = "1.0"
        self.hash_version: str = "v1"
        self.entries: List[ReportEntry] = []
        self.verdict: Verdict = Verdict.HEALTHY
        self.total_time_ms: float = 0.0
        self.percentages: Dict[str, float] = {}

    def set_total_time(self, total_time_ms: float):
        self.total_time_ms = total_time_ms
        self._calculate_percentages()

    def _calculate_percentages(self):
        """[PH1-RPR-002] Stage Percentage Breakdown for Bottleneck Detection."""
        if self.total_time_ms <= 0:
            return
        
        for entry in self.entries:
            pct = (entry.time_ms / self.total_time_ms) * 100
            self.percentages[entry.step_id] = round(pct, 2)

    def add_entry(self, step_id: str, severity: Severity, msg: str, time_ms: float = 0.0):
        self.entries.append(ReportEntry(step_id, severity, msg, time_ms))
        self._update_verdict(severity)

    def _update_verdict(self, severity: Severity):
        """
        [PH1-RPR-001] Verdict Aggregation Logic.
        Hierarchical resolution: CRITICAL/STRICT triggers ABORT.
        """
        current_verdict = resolve_verdict(severity, Severity.WARNING) # Default Intent
        if current_verdict == Verdict.FATAL_ABORT:
            self.verdict = Verdict.FATAL_ABORT
        elif current_verdict == Verdict.PROCEED_WITH_CAUTION and self.verdict != Verdict.FATAL_ABORT:
            self.verdict = Verdict.PROCEED_WITH_CAUTION

    def set_hash(self, ctx_hash: str):
        self.ctx_hash = ctx_hash

    def to_dict(self) -> Dict[str, Any]:
        performance = {}
        if self.total_time_ms > 0:
            for entry in self.entries:
                performance[entry.step_id] = {
                    "time_ms": entry.time_ms,
                    "percentage": round((entry.time_ms / self.total_time_ms) * 100, 2)
                }

        return {
            "slot_id": self.slot_id,
            "engine_version": self.engine_version,
            "schema_version": self.schema_version,
            "hash_version": self.hash_version,
            "ctx_hash": self.ctx_hash,
            "verdict": self.verdict.name,
            "total_time_ms": self.total_time_ms,
            "stage_performance": performance,
            "entries": [{
                "id": e.step_id,
                "severity": e.severity.name,
                "msg": e.msg,
                "time_ms": e.time_ms
            } for e in self.entries]
        }

class GroundTruthReport:
    """[PH2-CORE-06] Final Output for Compare & Ground Truth Engine."""
    def __init__(self, ctx_hash_a: str, ctx_hash_b: str):
        self.ctx_hash_a = ctx_hash_a
        self.ctx_hash_b = ctx_hash_b
        self.confidence_score: float = 0.0
        self.verdict: str = "PENDING"
        self.field_metrics: Dict[str, int] = {
            "total_fields": 0,
            "matched_fields": 0,
            "ignored_fields": 0,
            "strict_fields": 0,
            "optional_fields": 0
        }
        self.confidence_breakdown: Dict[str, float] = {
            "base_score": 0.0,
            "penalty": 0.0,
            "final_score": 0.0
        }
        self.mismatches: List[Dict[str, Any]] = []
        self.consistency_issues: List[Dict[str, Any]] = []

    def set_metrics(self, total: int, matched: int, ignored: int):
        self.field_metrics["total_fields"] = total
        self.field_metrics["matched_fields"] = matched
        self.field_metrics["ignored_fields"] = ignored

    def set_confidence(self, breakdown: Dict[str, float]):
        self.confidence_breakdown = breakdown
        self.confidence_score = breakdown["final_score"]
        if self.confidence_score >= 0.98:
            self.verdict = "ULTIMATE_TRUST"
        elif self.confidence_score >= 0.90:
            self.verdict = "HIGH_CONFIDENCE"
        elif self.confidence_score >= 0.70:
            self.verdict = "PROCEED_WITH_CAUTION"
        else:
            self.verdict = "INSECURE_INTERPRETATION"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "ctx_hash_a": self.ctx_hash_a,
            "ctx_hash_b": self.ctx_hash_b,
            "confidence_score": self.confidence_score,
            "verdict": self.verdict,
            "field_metrics": self.field_metrics,
            "confidence_breakdown": self.confidence_breakdown,
            "mismatches": self.mismatches,
            "consistency_issues": self.consistency_issues
        }
