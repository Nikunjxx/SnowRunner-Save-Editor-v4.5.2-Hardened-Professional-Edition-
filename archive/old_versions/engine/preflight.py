import os
import json
import zlib
from typing import List, Dict, Any, Optional
from dataclasses import dataclass, field

@dataclass
class PreflightIssue:
    type: str # STRUCTURAL, CORE, SYNC, LINKAGE, DISCOVERY, CROSS-SAVE, VEHICLE
    severity: str # LOW, MEDIUM, HIGH, CRITICAL
    issue: str
    suggested_fix: str
    fix_action: Optional[str] = None # Feature key for IntegrityManager
    metadata: Dict[str, Any] = field(default_factory=dict)

class PreflightReport:
    def __init__(self):
        self.issues: List[PreflightIssue] = []
        self.is_healthy = True
        self.critical_count = 0

    def add_issue(self, issue: PreflightIssue):
        self.issues.append(issue)
        self.is_healthy = False
        if issue.severity == "CRITICAL":
            self.critical_count += 1

class PreflightEngine:
    """
    Zero-Trust Save Auditor (v110.31.3+).
    Scans for logical corruption before full UI interaction.
    """
    def __init__(self, target_folder: str):
        self.target_folder = target_folder

    def audit_all(self, whitelist: List[str]) -> PreflightReport:
        report = PreflightReport()
        for filename in whitelist:
            path = os.path.join(self.target_folder, filename)
            if not os.path.exists(path):
                continue
            
            # 1. Structural Audit
            data = self._load_json_safe(path, report, filename)
            if not data:
                continue
            
            # 2. Key-Level Audits (Logic)
            if "CompleteSave" in filename:
                self._audit_complete_save(data, report, filename)
                
        return report

    def _load_json_safe(self, path: str, report: PreflightReport, filename: str) -> Optional[Dict[str, Any]]:
        try:
            with open(path, "rb") as f:
                raw_data = f.read()
            
            # Decompress if magic header present
            if raw_data.startswith(b"\x41\x4b\x05\x00") or raw_data.startswith(b"\xd3\xa6\x02\x00"):
                try:
                    raw_data = zlib.decompress(raw_data[4:])
                except Exception as e:
                    report.add_issue(PreflightIssue(
                        type="STRUCTURAL", severity="CRITICAL",
                        issue=f"Zlib corruption in {filename}",
                        suggested_fix="Restore from backup",
                    ))
                    return None
            
            decoded = raw_data.decode("utf-8", errors="ignore")
            # Handle potential null-terminator padding
            json_text = decoded.strip().split('\x00')[0]
            return json.loads(json_text)
        except json.JSONDecodeError as e:
            report.add_issue(PreflightIssue(
                type="STRUCTURAL", severity="CRITICAL",
                issue=f"Malformed JSON in {filename}: {str(e)[:100]}",
                suggested_fix="Standard Sanitizer should be run to reformat.",
                fix_action="diagnostic_check"
            ))
        except Exception as e:
            report.add_issue(PreflightIssue(
                type="STRUCTURAL", severity="MEDIUM",
                issue=f"Could not parse {filename}: {e}",
                suggested_fix="Ensure file permissions are correct."
            ))
        return None

    def _audit_complete_save(self, data: Dict[str, Any], report: PreflightReport, filename: str):
        # Anchor to SslValue
        ssl = data.get("SslValue", data) if "SslValue" in data or "CompleteSave" not in data else data.get("CompleteSave", {}).get("SslValue", {})
        
        # 1. CORE Check (Values)
        money = ssl.get("money")
        if money is not None and (not isinstance(money, int) or money < 0):
            report.add_issue(PreflightIssue(
                type="CORE", severity="MEDIUM",
                issue=f"Unusual money value detected: {money}",
                suggested_fix="Reset money to a safe value.",
                fix_action="add_money",
                metadata={"current": money}
            ))

        # 2. SYNC Check (Tasks)
        obj_states = ssl.get("objectiveStates", {})
        if isinstance(obj_states, dict):
            for obj_id, state in obj_states.items():
                if not isinstance(state, dict): continue
                if state.get("isFinished") and state.get("lastStatus") != 3:
                    # lastStatus=3 usually indicates success in modern builds
                    report.add_issue(PreflightIssue(
                        type="SYNC", severity="MEDIUM",
                        issue=f"Task '{obj_id}' is marked finished but status is inconsistent.",
                        suggested_fix="Reset quest state machine.",
                        fix_action="reset_task",
                        metadata={"obj_id": obj_id}
                    ))

        # 3. LINKAGE Check (Garages)
        garages = ssl.get("garagesData", {})
        discovered = ssl.get("discoveredObjects", [])
        # Heuristic: if a garage is in discoveredObjects but not in garagesData (active), it might be unrecoverable
        for obj in discovered:
            if "US_01_01_GARAGE" in str(obj).upper() and "us_01_01" not in garages:
                 report.add_issue(PreflightIssue(
                    type="LINKAGE", severity="HIGH",
                    issue="Garage 'Black River' discovered but not initialized in world state.",
                    suggested_fix="Force sync garage linkages.",
                    fix_action="fix_recovery"
                ))

        # 4. DISCOVERY Check
        upgrades = ssl.get("discoveredUpgrades", [])
        # We can add checks for upgrade counts vs static data here later (Phase 5)
