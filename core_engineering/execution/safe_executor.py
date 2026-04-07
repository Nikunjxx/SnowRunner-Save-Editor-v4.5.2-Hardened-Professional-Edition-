from core_engineering.logging import logger
from core_engineering.errors.error_facade import ErrorFacade
from typing import Callable, Any, Dict, Optional
import uuid

class SafeExecutor:
    """
    Standard Operating Gate for all critical actions.
    Mandates: Checkpoint -> Execute -> Log -> (Restore + Translate on fail).
    """
    
    def __init__(self, recovery_manager):
        self.recovery = recovery_manager

    def execute(self, operation: Callable, context: Optional[Dict[str, Any]] = None, affected_path: str = None) -> Dict[str, Any]:
        """
        Executes a callable within a safety-monitored context with correlation.
        """
        # 0. Generate Correlation Identity [PH4-TRACE-001]
        request_id = str(uuid.uuid4())
        context = context or {}
        context["request_id"] = request_id
        
        # 1. State Checkpoint [PH4-SEC-001]
        # [PH4-PERF-001] Dirty-Path Optimization Check
        self.recovery.checkpoint(affected_path)

        try:
            # 2. Synchronous Operation
            result = operation()

            # 3. Success Audit
            # Truncate context to prevent log-bloat [PH4-TRACE-002]
            safe_context = self._truncate_context(context)
            logger.info("Operation SUCCESS", safe_context)
            
            # Clean up checkpoint as it's no longer needed for rollback
            self.recovery.clear()
            
            return {
                "status": "SUCCESS",
                "result": result,
                "request_id": request_id
            }

        except Exception as e:
            # 4. Failure Isolation [PH4-SEC-002]
            # Record detailed exception to the session log
            safe_context = self._truncate_context(context)
            logger.error("Operation FAILED", {
                "error": str(e),
                "type": type(e).__name__,
                "context": safe_context,
                "severity": getattr(e, "severity", "ERROR")
            })

            # 5. Atomic Restoration [PH4-SEC-003]
            # Restore the memory state to prevent inconsistencies
            self.recovery.restore()

            # 6. Safe Translation [PH4-SEC-004]
            # Provide high-fidelity, user-safe message
            return {
                "status": "FAIL",
                "message": ErrorFacade.translate(e),
                "error_type": type(e).__name__,
                "request_id": request_id,
                "severity": getattr(e, "severity", "ERROR")
            }

    def _truncate_context(self, context: dict, max_len: int = 100) -> dict:
        """[PH4-TRACE-002] Prevents large JSON objects from bloating logs."""
        safe_ctx = {}
        for k, v in context.items():
            if isinstance(v, str) and len(v) > max_len:
                safe_ctx[k] = v[:max_len] + "..."
            elif isinstance(v, (list, dict)) and len(str(v)) > max_len * 2:
                safe_ctx[k] = f"<{type(v).__name__} size={len(v)} [TRUNCATED]>"
            else:
                safe_ctx[k] = v
        return safe_ctx
