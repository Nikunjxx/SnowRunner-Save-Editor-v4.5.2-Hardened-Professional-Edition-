from typing import List, Dict, Any
from learning.pattern_miner import PatternMiner
from learning.rule_suggester import suggest_progression_rules
from learning.mapping_suggester import suggest_mappings

class LearningEngine:
    """[PH2-LRN-005] Orchestrator for the Assisted Intelligence Layer."""
    
    def __init__(self):
        self.miner = PatternMiner()

    def run(self, diff_entries: List[Dict[str, Any]], unknown_paths: List[str], ctx_state: Dict[str, Any]) -> Dict[str, Any]:
        """
        Executes the learning cycle.
        1. Ingests raw diffs for pattern mining.
        2. Proposes rules for identified repeatable behaviors.
        3. Proposes mappings for unknown paths.
        """
        # 1. Mining Behavior
        self.miner.ingest(diff_entries)
        patterns = self.miner.analyze()
        
        # 2. Rule Proposals
        rule_proposals = suggest_progression_rules(patterns)
        
        # 3. Mapping Proposals
        mapping_proposals = suggest_mappings(unknown_paths, ctx_state)
        
        return {
            "patterns": patterns,
            "rule_proposals": rule_proposals,
            "mapping_proposals": mapping_proposals
        }
