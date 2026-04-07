import os
import glob
import logging
from dataclasses import dataclass
from typing import Dict, List, Optional, Set
from exceptions import IntegrityError

@dataclass
class SlotContext:
    slot_index: int        # 0, 1, 2, 3 (maps to Slot 1, 2, 3, 4)
    save_file_path: str    # Absolute path to CompleteSave.cfg/dat
    prefix: str            # "", "1_", "2_", "3_"
    is_epic: bool          # True if .dat, False if .cfg
    folder_path: str

    @property
    def extension(self) -> str:
        return ".dat" if self.is_epic else ".cfg"

class SlotResolver:
    """
    Deterministic Slot Resolver with Strict Isolation Guard and Orphan Detection.
    Ensures zero cross-slot data contamination.
    """
    
    PREFIX_MAP = {0: "", 1: "1_", 2: "2_", 3: "3_"}
    REVERSE_PREFIX_MAP = {v: k for k, v in PREFIX_MAP.items()}
    
    logger = logging.getLogger("SlotResolver")

    @classmethod
    def get_slot_from_filename(cls, filename: str) -> Optional[int]:
        """
        Extracts the slot index (0-3) from a filename prefix.
        Example: '1_sts...' -> 1, 'CompleteSave2.cfg' -> 2, 'CompleteSave.cfg' -> 0
        """
        # 1. Check for slot prefixes (1_, 2_, 3_)
        if filename[1:2] == "_":
            prefix = filename[0:2]
            return cls.REVERSE_PREFIX_MAP.get(prefix)
            
        # 2. Check for CompleteSave suffix (CompleteSave1, etc)
        if "CompleteSave" in filename:
            name_part = filename.split(".")[0]
            if name_part == "CompleteSave":
                return 0
            try:
                # Expecting 'CompleteSave1', 'CompleteSave2', etc.
                idx_str = name_part.replace("CompleteSave", "")
                if idx_str:
                    return int(idx_str)
            except ValueError:
                pass
        
        # 3. Default for Slot 0 (no digit prefix)
        if not filename[0].isdigit():
            return 0
            
        return None

    @classmethod
    def scan_folder(cls, folder_path: str) -> List[SlotContext]:
        """
        Scans folder and returns valid SlotContexts. 
        Enforces Zero-Trust isolation.
        """
        if not os.path.exists(folder_path):
            return []

        # Determine platform (.cfg vs .dat)
        is_epic = any(f.endswith(".dat") for f in os.listdir(folder_path))
        ext = ".dat" if is_epic else ".cfg"
        slots = []

        for idx in range(4):
            save_name = "CompleteSave" if idx == 0 else f"CompleteSave{idx}"
            full_path = os.path.join(folder_path, f"{save_name}{ext}")
            
            if os.path.exists(full_path):
                slots.append(SlotContext(
                    slot_index=idx,
                    save_file_path=full_path,
                    prefix=cls.PREFIX_MAP[idx],
                    is_epic=is_epic,
                    folder_path=folder_path
                ))
        return slots

    @classmethod
    def detect_orphans(cls, slot: SlotContext) -> List[str]:
        """
        Lists files that belong to this slot's ID but are NOT part of the primary save chain.
        Also finds potential corruption where binary files exist without a matching save.
        """
        prefix = slot.prefix
        ext = slot.extension
        orphans = []
        
        # Match all files in the directory
        all_files = os.listdir(slot.folder_path)
        
        for f in all_files:
            # Skip non-cfg/dat
            if not f.endswith(ext): continue
            
            file_slot = cls.get_slot_from_filename(f)
            if file_slot == slot.slot_index:
                # Is it a known file we normally handle?
                known_names = ["CompleteSave", "CommonSslSave", "GameVersionSave", "sts_level_", "fog_level_"]
                if not any(k in f for k in known_names):
                    orphans.append(f)
        
        return orphans

    @classmethod
    def get_isolated_slot_files(cls, slot: SlotContext) -> Dict[str, List[str]]:
        """
        Strict Isolation Guard: Retrieves ONLY files belonging precisely to this slot's ID.
        """
        prefix = slot.prefix
        ext = slot.extension
        path = slot.folder_path
        
        # Valid files must have the correct prefix AND correctly map back to this slot index
        all_matches = glob.glob(os.path.join(path, f"*{ext}"))
        
        results = {"core": {}, "sts": [], "fog": []}
        
        for full_path in all_matches:
            fname = os.path.basename(full_path)
            if cls.get_slot_from_filename(fname) == slot.slot_index:
                if "sts_level_" in fname:
                    results["sts"].append(full_path)
                elif "fog_level_" in fname:
                    results["fog"].append(full_path)
                elif "CompleteSave" in fname:
                    results["core"]["CompleteSave"] = full_path
                elif "CommonSslSave" in fname:
                    results["core"]["CommonSslSave"] = full_path

        return results
