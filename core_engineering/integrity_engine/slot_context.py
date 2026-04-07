"""
SnowRunner Slot Context (Phase 7)
---------------------------------
Identifies the active save slot and enforces deterministic file isolation.
Ensures that Slot 2 edits (CompleteSave1.cfg) only touch Slot 2 world-state files (1_sts_*.cfg).
"""

import os
import re

class SlotContext:
    def __init__(self, main_save_path: str):
        self.main_save_path = main_save_path
        self.filename = os.path.basename(main_save_path)
        self.slot_id = self._detect_slot_id()
        self.prefix = self._get_prefix()

    def _detect_slot_id(self) -> int:
        """Determines if this is Slot 1, 2, 3, or 4."""
        # Standard: CompleteSave.cfg, CompleteSave1.cfg, etc.
        match = re.search(r"CompleteSave(\d+)?", self.filename, re.I)
        if match:
            digit = match.group(1)
            if digit is None:
                return 1
            # Slot 2 is CompleteSave1, Slot 3 is CompleteSave2, etc. (0-indexed in filename)
            return int(digit) + 1
        return 1

    def _get_prefix(self) -> str:
        """Returns the filename prefix for related .sts and .fog files."""
        if self.slot_id == 1:
            return ""
        # Slot 2 (CompleteSave1) uses "1_" prefix for STS/Fog
        return f"{self.slot_id - 1}_"

    def resolve_file(self, base_pattern: str, region: str = None) -> str:
        """
        Resolves a base filename pattern (e.g. 'sts_level_{region}.cfg') 
        to the slot-specific filename.
        """
        filename = base_pattern
        if region:
            filename = filename.replace("{region}", region.lower())
        
        # Apply slot prefix
        return f"{self.prefix}{filename}"

    def __repr__(self):
        return f"<SlotContext Slot={self.slot_id} Prefix='{self.prefix}'>"
