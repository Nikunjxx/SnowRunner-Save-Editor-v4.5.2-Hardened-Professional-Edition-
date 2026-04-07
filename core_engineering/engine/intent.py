from dataclasses import dataclass, field
from typing import Dict, Any
from rules import Severity

@dataclass
class Intent:
    """
    Structured Schema for Operation Intent.
    Bridges user commands to the final transaction system.
    """
    category: str # (FINANCIAL / OBJECTIVE / EXPLORATION)
    intent_severity: Severity = Severity.WARNING
    target_values: Dict[str, Any] = field(default_factory=dict)
    
    def add_target(self, path: str, value: Any):
        self.target_values[path] = value

    @property
    def is_composite(self) -> bool:
        return len(self.target_values) > 1
