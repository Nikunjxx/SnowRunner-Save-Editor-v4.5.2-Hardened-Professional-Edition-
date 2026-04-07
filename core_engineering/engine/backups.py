import os
import shutil
import logging
from typing import Optional

logger = logging.getLogger("BackupEngine")

class BackupManager:
    """
    3-Stage Rotation Engine (.bak1, .bak2, .bak3)
    Prevents overwriting the 'last good' backup if multiple 
    corruptions happen in sequence.
    """
    
    @staticmethod
    def rotate_backups(file_path: str):
        """
        Shifts existing backups and creates a new .bak1
        """
        if not os.path.exists(file_path):
            return

        # 1. Shift: .bak2 -> .bak3, .bak1 -> .bak2
        for i in range(2, 0, -1):
            source = f"{file_path}.bak{i}"
            dest = f"{file_path}.bak{i+1}"
            if os.path.exists(source):
                shutil.move(source, dest)
                logger.info(f"BACKUP_ROTATE: Shifted {source} to {dest}")

        # 2. Create new .bak1
        dest_bak1 = f"{file_path}.bak1"
        shutil.copy2(file_path, dest_bak1)
        logger.info(f"BACKUP_CREATED: {dest_bak1}")

    @staticmethod
    def restore_latest(file_path: str) -> bool:
        """
        Restores the .bak1 version to the main file.
        """
        bak1 = f"{file_path}.bak1"
        if os.path.exists(bak1):
            shutil.copy2(bak1, file_path)
            logger.warning(f"ROLLBACK_COMPLETE: Restored {file_path} from backup.")
            return True
        return False
