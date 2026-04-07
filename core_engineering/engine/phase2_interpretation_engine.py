import logging
from collections import defaultdict
from typing import Any, Optional, Dict
from compare import RawDiffEntry, RawDiffResult
from classifier import MismatchType, Severity, DiffClassifier, ProgressionRules
from noise_filter import NoiseFilter
from learning.learning_engine import LearningEngine

logger = logging.getLogger("InterpretationEngine")

class InterpretationEngine:
    """[PH2-INT-001] The Semantic Director for Phase 2.4."""
    
    def __init__(self):
        # [PH2-INT-002] Intelligence Layer
        self.learning_engine = LearningEngine()
        
        # [PH2-INT-003] UNKNOWN Governance (Per-Run Reset)
        self.unknown_registry = defaultdict(int)
        self.current_raw_diffs = []
        self.current_ctx_state = {}

    def interpret(self, raw_result: RawDiffResult, ctx: Optional[dict] = None) -> Dict[str, Any]:
        """
        [PH2-INT-003] Orchestrates absolute classification with strict ordering.
        ORDER: 1. NOISE -> 2. EXPECTED_DELTA -> 3. UNKNOWN -> 4. TRUE_MISMATCH
        """
        ctx = ctx or {}
        grouped = {
            MismatchType.NOISE.value: [],
            MismatchType.EXPECTED_DELTA.value: [],
            MismatchType.UNKNOWN.value: [],
            MismatchType.TRUE_MISMATCH.value: [],
            MismatchType.TYPE_MISMATCH.value: [],
            MismatchType.STRUCTURAL_OFFSET.value: []
        }

        for diff in raw_result.diffs:
            path = diff.path
            old = diff.old_value
            new = diff.new_value
            
            # 1. Noise Filtering [PH2-INT-004]
            if NoiseFilter.is_noise(path):
                grouped[MismatchType.NOISE.value].append(self._to_entry(diff, MismatchType.NOISE))
                continue

            # 2. Semantic Rule Validation [PH2-INT-005]
            # [PH2-INT-006] Structural Reconciliation: Rules can override structural offsets
            if ProgressionRules.validate_progression(path, old, new, ctx):
                grouped[MismatchType.EXPECTED_DELTA.value].append(self._to_entry(diff, MismatchType.EXPECTED_DELTA))
                continue

            # 3. Structural Fallback [PH2-INT-007]
            # If no rule matches and it is structural, assign critical offset type.
            if diff.is_structural:
                m_type = MismatchType.TYPE_MISMATCH if old is not None and new is not None else MismatchType.STRUCTURAL_OFFSET
                grouped[m_type.value].append(self._to_entry(diff, m_type))
                continue

            # 4. UNKNOWN / TRUE_MISMATCH [PH2-INT-008]
            rule = ProgressionRules.get_rule(path)
            if not rule:
                self.unknown_registry[path] += 1
                grouped[MismatchType.UNKNOWN.value].append(self._to_entry(diff, MismatchType.UNKNOWN))
                continue

            # If rule exists but validation failed
            grouped[MismatchType.TRUE_MISMATCH.value].append(self._to_entry(diff, MismatchType.TRUE_MISMATCH))

        # 6. Accumulate Diffs for Learning
        self.current_raw_diffs = raw_result.diffs
        
        return {
            "grouped": grouped,
            "unknown_freq": dict(self.unknown_registry)
        }

    def learn(self) -> Dict[str, Any]:
        """[PH2-INT-005] Intelligence Orchestration Layer."""
        # Convert internal registry to format expected by LearningEngine
        unknown_paths = list(self.unknown_registry.keys())
        
        # Execute the learning cycles
        return self.learning_engine.run(
            diff_entries=[d.__dict__ for d in self.current_raw_diffs],
            unknown_paths=unknown_paths,
            ctx_state=self.current_ctx_state
        )

    def clear_unknowns(self):
        """[PH2-INT-006] Absolute Reset for Audit Determinism."""
        self.unknown_registry = defaultdict(int)
        self.current_raw_diffs = []

    def _to_entry(self, diff: RawDiffEntry, m_type: MismatchType) -> Dict[str, Any]:
        """Normalize the result into a reportable entry."""
        return {
            "path": diff.path,
            "type": m_type.value,
            "severity": DiffClassifier.get_severity(m_type).value,
            "old": diff.old_value,
            "new": diff.new_value,
            "classification": m_type.value
        }
