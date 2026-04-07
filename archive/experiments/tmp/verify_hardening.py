
import os
import time
import hashlib
import uuid
import sys
import tempfile
import shutil

# Add current dir to sys.path
sys.path.append(r'e:\Snow Runner New Tool')

from integrity_engine.manager import IntegrityManager

def test_hashing(test_dir, data_dir, remote_dir):
    print("--- Testing SHA-1 Hashing ---")
    dummy_path = os.path.join(test_dir, "test_file.cfg")
    with open(dummy_path, "wb") as f:
        f.write(b"SnowRunnerDataV1")
    
    # Minimal Init
    manager = IntegrityManager.__new__(IntegrityManager)
    manager.target_folder = test_dir
    
    h1 = manager._get_sha1_hash(dummy_path)
    print(f"Hash 1: {h1}")
    
    with open(dummy_path, "wb") as f:
        f.write(b"SnowRunnerDataV2") # Same length
    
    h2 = manager._get_sha1_hash(dummy_path)
    print(f"Hash 2: {h2}")
    
    assert h1 != h2, "SHA-1 failed to detect same-size content change!"
    print("✅ SHA-1 Detection Success")

def test_atomic_write(test_dir, data_dir, remote_dir):
    print("\n--- Testing Atomic Write ---")
    dummy_path = os.path.join(test_dir, "test_atomic.cfg")
    
    manager = IntegrityManager.__new__(IntegrityManager)
    manager.target_folder = test_dir
    
    data = b"AtomicDataVersion1"
    manager._atomic_write(dummy_path, data)
    
    with open(dummy_path, "rb") as f:
        read_data = f.read()
    
    assert read_data == data, "Atomic write data mismatch!"
    assert not os.path.exists(dummy_path + ".tmp"), "Temp file not cleaned up!"
    print("✅ Atomic Write Success")

def test_session_stale_detection(test_dir, data_dir, remote_dir):
    print("\n--- Testing STALE Detection (Optimized) ---")
    dummy_path = "CompleteSave.cfg"
    abs_dummy_path = os.path.join(test_dir, dummy_path)
    with open(abs_dummy_path, "wb") as f: f.write(b"Baseline")
    
    manager = IntegrityManager.__new__(IntegrityManager)
    manager.target_folder = test_dir
    manager.save_context = {"main": dummy_path, "global": None, "sts": {}, "fog": {}}
    manager.session_snapshot = {}
    manager.session_state = "CLEAN"
    
    manager.snapshot_context()
    
    valid, conflicts = manager.check_session_validity()
    assert valid, f"False positive on stale detection! Conflicts: {conflicts}"
    
    time.sleep(0.1)
    with open(abs_dummy_path, "wb") as f: f.write(b"Modified")
    
    valid, conflicts = manager.check_session_validity()
    assert not valid, "Failed to detect same-size tamper!"
    assert dummy_path in conflicts
    print("✅ Optimized Stale Detection Success")

if __name__ == "__main__":
    test_dir = tempfile.mkdtemp()
    data_dir = tempfile.mkdtemp()
    remote_dir = tempfile.mkdtemp()
    
    try:
        print(f"Testing in {test_dir}")
        test_hashing(test_dir, data_dir, remote_dir)
        test_atomic_write(test_dir, data_dir, remote_dir)
        test_session_stale_detection(test_dir, data_dir, remote_dir)
        print("\n🎉 ALL HARDENING TESTS PASSED")
    except Exception as e:
        import traceback
        traceback.print_exc()
        print(f"\n❌ TEST FAILED: {e}")
        sys.exit(1)
    finally:
        shutil.rmtree(test_dir)
        shutil.rmtree(data_dir)
        shutil.rmtree(remote_dir)
