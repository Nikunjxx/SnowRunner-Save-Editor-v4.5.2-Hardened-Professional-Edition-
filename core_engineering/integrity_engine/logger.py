import os
import json
import datetime
import uuid

class OperationLogger:
    """
    Persistent JSON-schema audit trail for save modifications.
    Stored at: app/snowrunner_save_editor_data/operations.log
    """
    def __init__(self, log_path: str):
        self.log_path = log_path
        if not os.path.exists(os.path.dirname(log_path)):
            os.makedirs(os.path.dirname(log_path), exist_ok=True)
        self.prune_logs()

    def prune_logs(self, max_entries: int = 500):
        """Trims the log file to the last N entries."""
        if not os.path.exists(self.log_path): return
        try:
            with open(self.log_path, 'r') as f:
                lines = f.readlines()
            if len(lines) > max_entries:
                with open(self.log_path, 'w') as f:
                    f.writelines(lines[-max_entries:])
                print(f"[Logger] Pruned logs to last {max_entries} entries.")
        except Exception as e:
            print(f"[Logger] Pruning failed: {e}")

    def log_operation(self, feature: str, region: str = "GLOBAL", duration_ms: int = 0, 
                      files_modified: list = None, status: str = "INFO", 
                      warnings: list = None, reason: str = None, before_hashes: dict = None, 
                      after_hashes: dict = None, version_detected: str = "Unknown"):
        entry = {
            "operation_id": str(uuid.uuid4()),
            "timestamp": datetime.datetime.now().isoformat(),
            "feature": feature,
            "region": region,
            "duration_ms": duration_ms,
            "files_modified": files_modified,
            "status": status,
            "warnings": warnings or [],
            "reason": reason,
            "before_hashes": before_hashes or {},
            "after_hashes": after_hashes or {},
            "version_detected": version_detected
        }
        
        try:
            with open(self.log_path, 'a') as f:
                f.write(json.dumps(entry) + "\n")
        except Exception as e:
            print(f"[Logger] Failed to write log: {e}")

    def get_logs(self, limit: int = 100) -> list:
        logs = []
        if not os.path.exists(self.log_path): return logs
        
        try:
            with open(self.log_path, 'r') as f:
                lines = f.readlines()
                for line in lines[-limit:]:
                    logs.append(json.loads(line))
        except Exception as e:
            print(f"[Logger] Failed to read logs: {e}")
        return logs[::-1] # Newest first
