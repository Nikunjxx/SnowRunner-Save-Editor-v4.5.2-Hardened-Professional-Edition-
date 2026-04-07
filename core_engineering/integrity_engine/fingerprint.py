import os
import json
import zlib
from typing import Dict, Any, List

class FingerprintEngine:
    """
    Analyzes SnowRunner save folders to detect game versions, formats, and DLC states.
    v110.40 Platinum: Focuses on SslValue anchoring and STS file counts.
    """
    def __init__(self, target_folder: str):
        self.target_folder = target_folder

    def detect_format(self) -> str:
        """Determines if the save is Steam (.cfg) or Epic/MS Store (.dat)."""
        files = os.listdir(self.target_folder)
        if any(f.endswith(".cfg") and "CompleteSave" in f for f in files):
            return "Steam (JSON/Zlib)"
        if any(f.endswith(".dat") and "CompleteSave" in f for f in files):
            return "Epic/MS Store (Binary/Zlib)"
        return "Unknown Format"

    def audit_version_hints(self) -> Dict[str, Any]:
        """Deep heuristic for version fingerprinting."""
        hints = {
            "version_code": "Unknown",
            "ssl_anchoring": False,
            "dlc_count": 0,
            "is_legacy": False
        }
        
        # 1. Check for SslValue in the main save
        for f in os.listdir(self.target_folder):
            if "CompleteSave" in f and (f.endswith(".cfg") or f.endswith(".dat")):
                try:
                    path = os.path.join(self.target_folder, f)
                    with open(path, 'rb') as rb: data = rb.read()
                    
                    # Decompress and check keys
                    if len(data) > 4:
                        payload = zlib.decompress(data[4:]).decode('utf-8', errors='replace')
                        if '"SslValue":' in payload:
                            hints["ssl_anchoring"] = True
                            hints["version_code"] = "v110.40+"
                        else:
                            hints["version_code"] = "Pre-v110.40"
                            hints["is_legacy"] = True
                except: pass
                break
        
        # 2. DLC Count based on STS files
        sts_files = [f for f in os.listdir(self.target_folder) if f.startswith("sts_level_")]
        hints["dlc_count"] = len(sts_files)
        
        return hints

    def generate_fingerprint(self) -> str:
        """Returns a concise version string for logging."""
        fmt = self.detect_format()
        hints = self.audit_version_hints()
        
        ver = hints["version_code"]
        dlc = hints["dlc_count"]
        anchoring = "SSL_A" if hints["ssl_anchoring"] else "LEGACY"
        
        return f"{ver} | {fmt} | {anchoring} | DLC:{dlc}"
