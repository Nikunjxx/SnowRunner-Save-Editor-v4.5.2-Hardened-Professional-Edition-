import sys
import os
import json
import logging
from datetime import datetime

# [PH2-SYS-001] Dynamic Workspace Path Injection
workspace_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
core_path = os.path.join(workspace_root, "core_engineering")
sys.path.append(core_path)
sys.path.append(os.path.join(core_path, "engine"))

from pipeline import EnginePipeline
from slot_resolver import SlotResolver
from compare import CompareEngine
from classifier import MismatchType
from phase2_interpretation_engine import InterpretationEngine
from learning.learning_engine import LearningEngine
from prioritizer import Prioritizer
from regression_guard import RegressionGuard
from scorer import ConfidenceScorer # [PH2-SYS-002] Shared Scorer
from consistency import ConsistencyAuditor

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("GroundTruthAudit")

def run_ultimate_audit():
    """
    [PH2-ORC-001] The Master Orchestrator for Phase 2.4.
    Hydration -> Compare -> Interpretation -> Learning -> Safety Loop.
    """
    logger.info("PH2-GT-001: Initiating Ultimate Ground Truth Audit (Hardened Phase 2.4)...")
    
    # 1. Resolve Slots
    mirror_path = r"E:\Snow Runner New Tool\test_data\steam_live_mirror"
    slots = SlotResolver.scan_folder(mirror_path)
    if len(slots) < 2:
        logger.error("AUDIT_BLOCKED: Minimum 2 slots required for Ground Truth comparison.")
        return

    # [PH2-GT-002] Selection Strategy: Slot 0 (Target) vs Slot 1 (Baseline)
    slot_a = slots[0]
    slot_b = slots[1]

    # 2. Pipeline Hydration
    pipe_a = EnginePipeline(slot_a)
    pipe_b = EnginePipeline(slot_b)
    (ctx_a, report_a), _ = pipe_a.run_hydration()
    (ctx_b, report_b), _ = pipe_b.run_hydration()

    if ctx_a is None or ctx_b is None:
        logger.error("AUDIT_BLOCKED: Hydration failed for one or more slots.")
        return

    # 3. Core Comparison [PH2-GT-003] -> Raw Diffs Only
    logger.info(f"Comparing Slot {slot_a.slot_index} (Target) vs Slot {slot_b.slot_index} (Baseline)...")
    raw_result = CompareEngine.diff(ctx_a, ctx_b)

    # 4. Semantic Interpretation [PH2-GT-004] -> Classified Interpretation
    engine = InterpretationEngine()
    audit_ctx = {"is_cross_session": slot_a.slot_index != slot_b.slot_index}
    interpretation = engine.interpret(raw_result, ctx=audit_ctx)
    grouped = interpretation["grouped"]

    # 5. Cross-File Consistency Audit [PH2-GT-005] -> Semantic Validation
    logger.info("Performing Cross-File Consistency Audit...")
    consistency_issues = ConsistencyAuditor.audit_context(ctx_a)

    # 6. Confidence Scoring [PH2-GT-006] -> Two-Stage Verdict
    # 4. Scoring [PH2-GT-004]
    # Scorer v2.4.2 explicit counters
    score_result = ConfidenceScorer.compute(
        matched=raw_result.matched_count,
        expected=len(grouped[MismatchType.EXPECTED_DELTA.value]),
        noise=len(grouped[MismatchType.NOISE.value]),
        unknown=len(grouped[MismatchType.UNKNOWN.value]),
        true_mismatch=len(grouped[MismatchType.TRUE_MISMATCH.value]),
        structural_offset=len(grouped[MismatchType.STRUCTURAL_OFFSET.value]),
        type_mismatch=len(grouped[MismatchType.TYPE_MISMATCH.value]),
        total=raw_result.total_count
    )
    
    # [PH2-GT-005] Verbose Violation Reporting
    if grouped[MismatchType.TRUE_MISMATCH.value]:
        logger.warning(f"CRITICAL: {len(grouped[MismatchType.TRUE_MISMATCH.value])} TRUE_MISMATCH violations detected!")
        for m in grouped[MismatchType.TRUE_MISMATCH.value][:10]:
            logger.warning(f"  -> VIOLATION: {m['path']} (Old: {m['old']} | New: {m['new']})")

    # 7. Prioritization & Governance [PH2-GT-007] -> Unknown Path Ranking
    top_unknowns = Prioritizer.prioritize(interpretation["unknown_freq"])

    # 8. Learning Cycle [PH2-GT-008] -> Proposal Generation
    learning_engine = LearningEngine()
    proposals = learning_engine.run(
        diff_entries=grouped["UNKNOWN"], # We only learn from UNKNOWNs initially
        unknown_paths=list(interpretation["unknown_freq"].keys()),
        ctx_state=ctx_a.state
    )

    # 9. Safety Latch (Regression Guard) [PH2-GT-009]
    metrics = {
        "confidence": score_result["score"],
        "true_mismatch": len(grouped["TRUE_MISMATCH"]),
        "unknown": len(grouped["UNKNOWN"])
    }
    regression_status = RegressionGuard.check_regression(metrics)
    logger.info(f"REGRESSION_GUARD_STATUS: {regression_status}")

    # 10. Report Generation
    report = {
        "timestamp": datetime.now().isoformat(),
        "ctx_hash_a": ctx_a._data.get("hash"),
        "ctx_hash_b": ctx_b._data.get("hash"),
        "confidence_score": score_result["score"],
        "verdict": score_result["verdict"],
        "regression_status": regression_status,
        "metrics": {
            "total_fields": raw_result.total_count,
            "matched": raw_result.matched_count,
            "noise": len(grouped["NOISE"]),
            "expected_delta": len(grouped["EXPECTED_DELTA"]),
            "unknown": len(grouped["UNKNOWN"]),
            "true_mismatch": len(grouped["TRUE_MISMATCH"])
        },
        "top_priorities": top_unknowns[:20], # Focus on Top 20 as requested
        "consistency_issues": consistency_issues,
        "proposals": proposals,
        "mismatches": grouped # Detailed traces for every classified path
    }

    report_path = os.path.join(core_path, "logs", "ground_truth_report_v2_4.json")
    with open(report_path, "w") as f:
        json.dump(report, f, indent=4)

    logger.info(f"PH2-GT-COMPLETE: Hardened Report generated at {report_path}")
    
    counts = score_result["counts"]
    logger.info(f"Audit Summary: Score={score_result['score']}, Verdict={score_result['verdict']}")
    logger.info(f"Metrics: MATCHED={counts['matched']}, EXPECTED={counts['expected_delta']}, UNKNOWN={counts['unknown']}, MISMATCH={counts['true_mismatch']}, STRUCTURAL={counts['structural_offset']}")

if __name__ == "__main__":
    run_ultimate_audit()
