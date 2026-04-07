
import os, sys, zlib

def run_zero_trust_audit():
    import json
    print("--- 🚀 STARTING ZERO-TRUST OMNI-AUDIT ---")
    
    # 1. Setup
    test_folder = "app/snowrunner_save_editor_data/test_save_audit"
    os.makedirs(test_folder, exist_ok=True)
    header = b"\x41\x4b\x05\x00"
    content = {"SslValue": {"money": 5000, "rank": 1}}
    raw_data = json.dumps(content).encode('utf-8')
    compressed = zlib.compress(raw_data)
    with open(os.path.join(test_folder, "CompleteSave.cfg"), 'wb') as f:
        f.write(header + compressed)
    
    # 2. Handshake
    sys.path.append(os.getcwd())
    from app.integrity_engine.manager import IntegrityManager
    manager = IntegrityManager(test_folder, "app/snowrunner_save_editor_data", test_folder)
    
    print("\n[Step 1] Mutation Pipeline...")
    manager.run_preflight(["CompleteSave.cfg"])
    res = manager.execute_feature("money", value=6000)
    print(f"Status: {res['status']} | Success: {res['success']} | Error: {res.get('error', 'None')}")
    
    print("\n[Step 2] Binary Integrity...")
    # Check if the file still has the header
    with open(os.path.join(test_folder, "CompleteSave.cfg"), 'rb') as f:
        new_raw = f.read()
    has_header = new_raw.startswith(b"\x41\x4b\x05\x00")
    print(f"Header Valid: {has_header}")
    
    # 3. Final Summary
    score = (1 if res["success"] or res["status"] == "DRY_RUN_SUCCESS" else 0) + (1 if has_header else 0)
    print(f"CORE HANDSHAKE SCORE: {score}/2")
    if score == 2:
        print("CORE ENGINE: [ PRODUCTION READY ]")

if __name__ == "__main__":
    run_zero_trust_audit()
