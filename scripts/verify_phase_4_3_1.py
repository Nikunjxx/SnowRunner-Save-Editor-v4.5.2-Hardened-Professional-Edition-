# [PH4-VER-INTEL] Phase 4.3.1 Production Intelligence Drill
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
from core_engineering.errors.exceptions import ValidationError

def run_intel_drill():
    print("Initiating Phase 4.3.1 Production Intelligence Drill...")
    
    # 1. Foundation Load
    mpr = MapRunner()
    validator = FieldValidator(mpr)
    engine = MutationEngine(mpr, validator)
    recovery = RecoveryManager(engine)
    executor = SafeExecutor(recovery)
    
    initial_state = {"derived.player.money": 100}
    engine.set_state(initial_state)
    
    # --- DRILL 1: STRUCTURED LOG VALIDATION ---
    print("\nDRILL 1: Verifying Structured JSON Logging...")
    executor.execute(lambda: True, context={"drill": "intel_1"})
    
    log_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "logs"))
    logs = [f for f in os.listdir(log_dir) if f.endswith(".log")]
    if not logs: 
         print("DRILL 1 FAILURE: No log file found.")
         return
         
    last_log = os.path.join(log_dir, sorted(logs)[-1])
    with open(last_log, "r") as f:
         lines = f.readlines()
         # The logging system might have multiple records, get the one from our executor
         # Note: logging module might add its own prefix if not configured correctly for raw json
         for line in reversed(lines):
              if "intel_1" in line:
                   try:
                        # Extract the JSON part if there is a prefix
                        # (We set formatter as %(asctime)s | %(levelname)s | %(message)s)
                        json_str = line.split("|")[-1].strip()
                        log_data = json.loads(json_str)
                        
                        if all(k in log_data for k in ["time", "level", "msg", "ctx"]):
                             print(f"DRILL 1 SUCCESS: Structured Log Verified: {log_data['msg']}")
                        else:
                             print(f"DRILL 1 FAILURE: Log missing keys: {log_data.keys()}")
                             return
                        break
                   except Exception as e:
                        print(f"DRILL 1 FAILURE: Log line is not valid JSON: {line} -> {e}")
                        return
    
    # --- DRILL 2: GRANULARITY VALIDATION ---
    print("\nDRILL 2: Verifying Granular Error Feedback...")
    # Trigger validation failure with specific message
    res = executor.execute(
        lambda: engine.apply_change("player.money", -500),
        context={"drill": "intel_2"}
    )
    
    if res["status"] == "FAIL":
         message = res["message"]
         # Expected: "Invalid action. Details: Rejection: Money cannot be negative."
         if "Details: Rejection: Money cannot be negative." in message:
              print(f"DRILL 2 SUCCESS: Granular error feedback verified: {message}")
         else:
              print(f"DRILL 2 FAILURE: Granular details missing: {message}")
              return
    else:
         print(f"DRILL 2 FAILURE: Unexpected result: {res}")
         return

    print("\n--- PHASE 4.3.1 AUDIT COMPLETE: INTELLIGENCE REFINED ---")

if __name__ == "__main__":
    run_intel_drill()
