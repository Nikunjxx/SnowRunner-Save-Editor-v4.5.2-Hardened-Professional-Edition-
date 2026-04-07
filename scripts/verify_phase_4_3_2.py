# [PH4-VER-LIFE] Phase 4.3.2 Lifecycle & Tracing Drill
import sys
import os
import json

# Absolute Pathing [PH4-ARCH-ROOT]
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from core_engineering.maprunner.maprunner import MapRunner
from core_engineering.mapper.validators import FieldValidator
from core_engineering.engine.mutation_engine import MutationEngine
from core_engineering.recovery.recovery_manager import RecoveryManager
from core_engineering.execution.safe_executor import SafeExecutor
from core_engineering.errors.exceptions import TransactionError

def run_lifecycle_drill():
    print("Initiating Phase 4.3.2 Lifecycle & Tracing Drill...")
    
    # 1. Foundation Load
    mpr = MapRunner()
    validator = FieldValidator(mpr)
    engine = MutationEngine(mpr, validator)
    recovery = RecoveryManager(engine)
    executor = SafeExecutor(recovery)
    
    engine.set_state({"player.money": 100})
    
    # --- DRILL 1: CORRELATION ID TRACING ---
    print("\nDRILL 1: Verifying Correlation ID Consistency...")
    res = executor.execute(lambda: True, context={"drill": "life_1"})
    request_id = res["request_id"]
    
    log_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "logs"))
    logs = [f for f in os.listdir(log_dir) if f.endswith(".log")]
    last_log = os.path.join(log_dir, sorted(logs)[-1])
    
    with open(last_log, "r") as f:
         lines = f.readlines()
         found_id = False
         for line in reversed(lines):
              if request_id in line:
                   found_id = True
                   break
         if found_id:
              print(f"DRILL 1 SUCCESS: Trace established across log and result: {request_id}")
         else:
              print(f"DRILL 1 FAILURE: Request ID {request_id} not found in logs.")
              return

    # --- DRILL 2: CONTEXT TRUNCATION ---
    print("\nDRILL 2: Verifying Context Truncation (Anti-Bloat)...")
    huge_data = "X" * 5000
    res = executor.execute(lambda: True, context={"huge": huge_data, "drill": "life_2"})
    
    with open(last_log, "r") as f:
         lines = f.readlines()
         for line in reversed(lines):
              if "life_2" in line:
                   # Verify length of the message is sane (not 5000+)
                   if len(line) < 1000:
                        print(f"DRILL 2 SUCCESS: Context truncated. Log line length: {len(line)} (< 5000).")
                   else:
                        print(f"DRILL 2 FAILURE: Log line is too large ({len(line)} bytes)!")
                        return
                   break

    # --- DRILL 3: SEVERITY ESCALATION ---
    print("\nDRILL 3: Verifying Severity Escalation Propagation...")
    def fail_critical():
         raise TransactionError("System Disk Unreachable (Mock)")
         
    res = executor.execute(fail_critical, context={"drill": "life_3"})
    if res["status"] == "FAIL" and res["severity"] == "CRITICAL":
         print(f"DRILL 3 SUCCESS: Critical severity propagated. Message: {res['message']}")
    else:
         print(f"DRILL 3 FAILURE: Severity mismatch: {res.get('severity')}")
         return

    print("\n--- PHASE 4.3.2 AUDIT COMPLETE: OPERATIONAL HARDENING PROVED ---")

if __name__ == "__main__":
    run_lifecycle_drill()
