import os
import json
import time
from typing import Dict, Any

class ObservabilityEngine:
    """
    Tracks and persists aggregate system metrics for the High-Safety Integrity Pipeline.
    Stored at: app/snowrunner_save_editor_data/metrics.json
    """
    def __init__(self, metrics_path: str):
        self.metrics_path = metrics_path
        self.session_start = time.time()
        self.MAX_HISTORY = 500
        self.metrics = self._load_metrics()

    def _load_metrics(self) -> Dict[str, Any]:
        if os.path.exists(self.metrics_path):
            try:
                with open(self.metrics_path, 'r') as f:
                    data = json.load(f)
                    if "history" not in data: data["history"] = []
                    return data
            except: pass
        
        return {
            "total_mutations": 0,
            "successful_mutations": 0,
            "failed_mutations": 0,
            "blocked_mutations": 0,
            "total_bytes_processed": 0,
            "total_duration_ms": 0,
            "last_reset": time.time(),
            "history": []
        }

    def _save_metrics(self):
        try:
            # Prune history before saving
            if len(self.metrics.get("history", [])) > self.MAX_HISTORY:
                self.metrics["history"] = self.metrics["history"][-self.MAX_HISTORY:]
            
            with open(self.metrics_path, 'w') as f:
                json.dump(self.metrics, f, indent=4)
        except Exception as e:
            print(f"[Observability] Metric persistence failed: {e}")

    def record_mutation(self, status: str, duration_ms: int, bytes_processed: int, feature: str = "unknown"):
        """Updates aggregate metrics and pushes to pruned history."""
        self.metrics["total_mutations"] += 1
        self.metrics["total_duration_ms"] += duration_ms
        self.metrics["total_bytes_processed"] += bytes_processed
        
        if status.upper() in ["SUCCESS", "DRY_RUN_SUCCESS"]:
            self.metrics["successful_mutations"] += 1
        elif status.upper() == "BLOCKED":
            self.metrics["blocked_mutations"] += 1
        else:
            self.metrics["failed_mutations"] += 1
            
        # Add to history for anomaly detection (Phase 11 requested)
        self.metrics["history"].append({
            "timestamp": time.time(),
            "feature": feature,
            "status": status,
            "duration_ms": duration_ms
        })
            
        self._save_metrics()

    def get_summary(self) -> Dict[str, Any]:
        """Provides a user-friendly summary of system health."""
        total = self.metrics.get("total_mutations", 0)
        success_rate = (self.metrics.get("successful_mutations", 0) / total * 100) if total > 0 else 0
        avg_duration = (self.metrics.get("total_duration_ms", 0) / total) if total > 0 else 0
        
        return {
            "Total Actions": total,
            "Success Rate": f"{success_rate:.1f}%",
            "Avg Performance": f"{avg_duration:.0f}ms",
            "Data Throughput": f"{self.metrics.get('total_bytes_processed', 0) / 1024 / 1024:.1f}MB",
            "Uptime": f"{(time.time() - self.session_start) / 60:.1f}m"
        }

    def reset_metrics(self):
        """Wipes the aggregate counters."""
        self.metrics = {
            "total_mutations": 0,
            "successful_mutations": 0,
            "failed_mutations": 0,
            "blocked_mutations": 0,
            "total_bytes_processed": 0,
            "total_duration_ms": 0,
            "last_reset": time.time()
        }
        self._save_metrics()
