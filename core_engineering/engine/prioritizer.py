from typing import Dict, List, Tuple

class Prioritizer:
    """[PH2-GOV-001] Impact-weighted path scoring for Phase 2.4 governance."""
    
    @staticmethod
    def prioritize(unknown_registry: Dict[str, int]) -> List[Tuple[str, int]]:
        """
        Prioritizes paths based on impact and frequency.
        Weighting: Money/Rank/Progression = 5, Structural = 5, Others = 1-3.
        """
        scored = []

        for path, count in unknown_registry.items():
            # [PH2-GOV-002] Multi-level impact weighting
            impact = 1
            path_lower = path.lower()
            
            # High Impact: Gameplay Core
            if any(k in path_lower for k in ["money", "rank", "experience", "cash", "balance"]):
                impact = 5
            # High Impact: Mission/Map Progression
            elif any(k in path_lower for k in ["progression", "objective", "contract", "waypoint"]):
                impact = 5
            # High Impact: Discovery/Unlocks
            elif any(k in path_lower for k in ["unlocked", "discovered", "persistent"]):
                impact = 4
            # Medium Impact: Stats
            elif "stats" in path_lower:
                impact = 3
            
            # Final Score: impact weighted by frequency
            score = count * impact
            scored.append((path, score))

        # Return sorted by score descending
        return sorted(scored, key=lambda x: x[1], reverse=True)
