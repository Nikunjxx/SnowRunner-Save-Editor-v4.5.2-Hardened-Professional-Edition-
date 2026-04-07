import os
import shutil
import hashlib
import logging
from typing import List, Dict, Tuple

# Execution Mandate: PH1-MIR-001
# Tracking ID: MIRROR_DATA_CHKSUM

LOG_PATH = r"E:\Snow Runner New Tool\core_engineering\logs\engine_status.log"
os.makedirs(os.path.dirname(LOG_PATH), exist_ok=True)

# Configure Structured Logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.FileHandler(LOG_PATH),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("MirrorEngine")

def calculate_checksum(file_path: str) -> str:
    """Computes SHA-256 for integrity verification."""
    sha256_hash = hashlib.sha256()
    with open(file_path, "rb") as f:
        for byte_block in iter(lambda: f.read(4096), b""):
            sha256_hash.update(byte_block)
    return sha256_hash.hexdigest()

def mirror_data(src_path: str, dest_path: str):
    """
    Safely mirrors Steam data to a local directory with bit-level validation.
    Skips locked files to prevent engine crashes.
    """
    logger.info(f"PH1-MIR-001: Initiating Mirror Mode from {src_path}")
    
    if not os.path.exists(src_path):
        logger.critical(f"Source path not found: {src_path}")
        return

    os.makedirs(dest_path, exist_ok=True)
    
    report: List[Dict] = []
    
    # We only care about .cfg and binary .cfg files in the remote folder
    # In some SnowRunner versions, these are .dat
    target_exts = (".cfg", ".dat")
    
    files_to_copy = [f for f in os.listdir(src_path) if f.endswith(target_exts)]
    logger.info(f"Detected {len(files_to_copy)} candidate files for mirroring.")

    for filename in files_to_copy:
        src_file = os.path.join(src_path, filename)
        dest_file = os.path.join(dest_path, filename)
        
        try:
            # 1. Attempt to open for reading to check for Locks
            with open(src_file, 'rb') as f:
                pass
            
            # 2. Copy the file
            shutil.copy2(src_file, dest_file)
            
            # 3. Verify Checksums
            src_hash = calculate_checksum(src_file)
            dest_hash = calculate_checksum(dest_file)
            
            if src_hash == dest_hash:
                logger.info(f"Matched: {filename} (Hash: {src_hash[:8]}...)")
                report.append({"file": filename, "status": "VERIFIED", "hash": src_hash})
            else:
                logger.error(f"Integrity Mismatch: {filename}")
                report.append({"file": filename, "status": "CHKSUM_FAIL"})
                
        except PermissionError:
            logger.warning(f"Skipped: {filename} (File locked by Game/Steam)")
            report.append({"file": filename, "status": "LOCKED"})
        except Exception as e:
            logger.error(f"Fatal copy error: {filename} - {str(e)}")
            report.append({"file": filename, "status": "ERROR", "msg": str(e)})

    # Final Audit Summary
    success_count = sum(1 for r in report if r["status"] == "VERIFIED")
    locked_count = sum(1 for r in report if r["status"] == "LOCKED")
    
    logger.info(f"Mirroring Complete. [Verified: {success_count}] [Locked/Skipped: {locked_count}]")
    
    # Write full diagnostic for Phase 2
    snapshot_path = os.path.join(dest_path, "mirror_diagnostic_report.json")
    with open(snapshot_path, "w", encoding="utf-8") as f:
        import json
        json.dump({"report": report, "stats": {"total": len(files_to_copy), "verified": success_count}}, f, indent=4)

if __name__ == "__main__":
    STEAM_PATH = r"C:\Program Files (x86)\Steam\userdata\996096852\1465360\remote"
    MIRROR_PATH = r"E:\Snow Runner New Tool\test_data\steam_live_mirror"
    mirror_data(STEAM_PATH, MIRROR_PATH)
