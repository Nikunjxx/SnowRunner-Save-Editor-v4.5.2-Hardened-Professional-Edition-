# [PH4-REC-001] Engine State Recovery Manager
import copy
from typing import Any, Dict

class RecoveryManager:
    """
    Guarantees safe engine-state fallback.
    Prevents memory corruption or inconsistent memory states after failures.
    """
    
    def __init__(self, engine):
        self.engine = engine
        self._checkpoint: Dict[str, Any] = None

    def checkpoint(self, affected_path: str = None):
        """
        [PH4-PERF-001] Dirty-Path Checkpointing.
        Captures only the necessary branches for restoration.
        """
        if affected_path:
             # Extract root key (e.g. 'CompleteSave' from 'CompleteSave.SslValue...')
             root_key = affected_path.split(".")[0] if "." in affected_path else affected_path
             if root_key in self.engine.state:
                  # Partial clone
                  self._checkpoint = {root_key: copy.deepcopy(self.engine.state[root_key])}
                  return

        # Full fallback if no path provided
        self._checkpoint = copy.deepcopy(self.engine.state)

    def restore(self):
        """Restores the engine state from the partial or full checkpoint."""
        if self._checkpoint is not None:
             # Merge partial or replace full
             for k, v in self._checkpoint.items():
                  self.engine.state[k] = v
             
    def clear(self):
        """Discards the current checkpoint after successful commitment."""
        self._checkpoint = None
