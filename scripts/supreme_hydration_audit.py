import os
import sys
import json
import logging

# [PH1-AUD-001] Supreme Audit Script
# Adding core_engineering to path for imports
sys.path.append(r"E:\Snow Runner New Tool\core_engineering\engine")

from slot_resolver import SlotResolver, SlotContext
from pipeline import EnginePipeline
from report import Verdict

# Configure Logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')
logger = logging.getLogger("SupremeAudit")

def run_master_audit(mirror_path: str):
    """
    Executes a clinical hydration audit against the mirrored save data.
    Generates the first Supreme Hydration Report (V1.3).
    """
    logger.info("PH1-AUD-001: Initiating High-Integrity Hydration Audit...")
    
    # 1. Resolve Slots
    slots = SlotResolver.scan_folder(mirror_path)
    if not slots:
        logger.error(f"AUDIT_FAIL: No valid save slots found in {mirror_path}")
        return

    logger.info(f"Detected {len(slots)} valid slots for audit.")
    
    final_reports = []

    # 2. Execute Pipeline for each Slot
    for slot in slots:
        logger.info(f"--- Auditing Slot {slot.slot_index} ({slot.prefix}CompleteSave) ---")
        
        # [PH1-PIP-001] Single Entry Point
        pipeline = EnginePipeline(slot)
        # Handle the tuple return (result, elapsed) from the decorator
        (frozen_ctx, report), total_time = pipeline.run_hydration()
        
        status = "SUCCESS" if report.verdict != Verdict.FATAL_ABORT else "FAILED"
        logger.info(f"Slot {slot.slot_index} Audit: {status} (Verdict: {report.verdict.name})")
        
        final_reports.append(report.to_dict())

    # 3. Final Artifact Generation
    output_path = r"E:\Snow Runner New Tool\core_engineering\logs\supreme_audit_v1_3.json"
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(final_reports, f, indent=4)
    
    logger.info(f"PH1-AUD-COMPLETE: Master report generated at {output_path}")

if __name__ == "__main__":
    MIRROR_PATH = r"E:\Snow Runner New Tool\test_data\steam_live_mirror"
    run_master_audit(MIRROR_PATH)
