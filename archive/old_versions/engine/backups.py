import os
import shutil
import zipfile
import datetime
import json
import re
from typing import List, Optional, Dict, Any

class BackupManager:
    def __init__(self, data_dir: str, max_deltas: int = 5):
        self.data_dir = data_dir
        self.backup_dir = os.path.join(data_dir, "integrity_backups")
        self.max_deltas = max_deltas
        self.full_backup_name = "full_root_backup.zip"
        self.manifest_path = os.path.join(self.backup_dir, "backup_manifest.json")
        self._session_full_backup_done = False
        
        if not os.path.exists(self.backup_dir):
            os.makedirs(self.backup_dir, exist_ok=True)
        
        self._load_manifest()

    def _load_manifest(self):
        if os.path.exists(self.manifest_path):
            with open(self.manifest_path, 'r') as f:
                self.manifest = json.load(f)
        else:
            self.manifest = {"deltas": [], "full": None}

    def _save_manifest(self):
        with open(self.manifest_path, 'w') as f:
            json.dump(self.manifest, f, indent=2)

    def trigger_backup(self, source_dir: str, modified_files: List[str] = None):
        """
        Triggers the hybrid backup logic. 
        If it's the first run of the session, does a full ZIP.
        Otherwise, does a delta ZIP of modified_files.
        """
        if not self._session_full_backup_done:
            self._create_full_backup(source_dir)
            self._session_full_backup_done = True
        elif modified_files:
            self._create_delta_backup(source_dir, modified_files)

    def _create_full_backup(self, source_dir: str):
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        target_path = os.path.join(self.backup_dir, self.full_backup_name)
        
        # Simple overwrite for the one-and-only full backup
        # But we actually keep it timestamped inside if we want, 
        # let's stick to the 1-full requirement.
        with zipfile.ZipFile(target_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
            for root, _, files in os.walk(source_dir):
                for file in files:
                    if file.endswith('.cfg') or file.endswith('.dat'):
                        full_path = os.path.join(root, file)
                        rel_path = os.path.relpath(full_path, source_dir)
                        zipf.write(full_path, rel_path)
        
        self.manifest["full"] = {
            "name": self.full_backup_name,
            "timestamp": timestamp
        }
        self._save_manifest()
        print(f"[Backup] Full root backup created: {self.full_backup_name}")

    def _create_delta_backup(self, source_dir: str, modified_files: List[str]):
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        delta_name = f"delta_{timestamp}.zip"
        target_path = os.path.join(self.backup_dir, delta_name)
        
        import hashlib
        file_hashes = {}
        with zipfile.ZipFile(target_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
            for f in modified_files:
                abs_f = f if os.isabs(f) else os.path.join(source_dir, f)
                if os.path.isfile(abs_f):
                    rel_path = os.path.relpath(abs_f, source_dir)
                    with open(abs_f, "rb") as bf:
                        content = bf.read()
                        file_hashes[rel_path] = hashlib.sha256(content).hexdigest()
                    zipf.write(abs_f, rel_path)
        
        self.manifest["deltas"].append({
            "name": delta_name,
            "timestamp": timestamp,
            "files": list(file_hashes.keys()),
            "hashes": file_hashes
        })
        
        # FIFO Pruning
        while len(self.manifest["deltas"]) > self.max_deltas:
            oldest = self.manifest["deltas"].pop(0)
            oldest_path = os.path.join(self.backup_dir, oldest["name"])
            if os.path.exists(oldest_path):
                os.remove(oldest_path)
                print(f"[Backup] Pruned oldest delta: {oldest['name']}")

        self._save_manifest()
        print(f"[Backup] Delta backup created: {delta_name} ({len(modified_files)} files with hashes)")

    def verify_rollback(self, target_dir: str, delta_manifest: Dict[str, Any]) -> bool:
        """Byte-for-byte verification of the folder state against the snapshot hashes."""
        import hashlib
        expected_hashes = delta_manifest.get("hashes", {})
        
        for rel_path, expected_hash in expected_hashes.items():
            abs_path = os.path.join(target_dir, rel_path)
            if not os.path.exists(abs_path):
                print(f"[Backup] Verification FAILED: File missing after restore: {rel_path}")
                return False
            
            with open(abs_path, "rb") as f:
                actual_hash = hashlib.sha256(f.read()).hexdigest()
            
            if actual_hash != expected_hash:
                print(f"[Backup] Verification FAILED: Hash mismatch for {rel_path}")
                return False
        
        print(f"[Backup] Verification SUCCESS: All {len(expected_hashes)} files matched snapshot.")
        return True

    def restore_last_delta(self, target_dir: str) -> bool:
        """Atomic rollback from the most recent delta with byte-level verification."""
        if not self.manifest["deltas"]:
            print("[Backup] No deltas available for restore.")
            return False
            
        last = self.manifest["deltas"][-1]
        last_path = os.path.join(self.backup_dir, last["name"])
        
        try:
            with zipfile.ZipFile(last_path, 'r') as zipf:
                for name in zipf.namelist():
                    zipf.extract(name, target_dir)
            
            # Post-Restore Verification (v110.31 Hardening)
            return self.verify_rollback(target_dir, last)
            
        except Exception as e:
            print(f"[Backup] Restore failed: {e}")
            return False
