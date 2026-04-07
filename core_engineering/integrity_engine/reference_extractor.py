import os
import zlib
import json
import collections
from typing import Dict, Any, Set, List

MAGIC_AK = b'\x41\x4b\x05\x00'
MAGIC_D3 = b'\xd3\xa6\x02\x00'

class ReferenceExtractor:
    """
    Extracts patterns, schemas, and completion markers from the 100% reference save (Remote2).
    This serves as the 'Gold Standard' baseline for validation.
    """
    def __init__(self, remote2_path: str, cache_file: str, version: str = "110.30-Platinum"):
        self.remote2_path = remote2_path
        self.cache_file = cache_file
        self.current_version = version
        self.data = {
            "version": self.current_version,
            "global_patterns": {},
            "region_patterns": collections.defaultdict(dict),
            "headers": {},
            "schemas": {}
        }

    def _decompress(self, data: bytes) -> bytes:
        if data.startswith(MAGIC_AK) or data.startswith(MAGIC_D3):
            try:
                return zlib.decompress(data[4:])
            except zlib.error:
                return data
        return data

    def extract_all(self, force: bool = False, progress_callback: Any = None):
        """Perform deep scan of Remote2 and save patterns to cache."""
        if not force and os.path.exists(self.cache_file):
            try:
                with open(self.cache_file, 'r') as f:
                    cached_data = json.load(f)
                    if cached_data.get("version") == self.current_version:
                        if progress_callback: progress_callback("✔ Patterns loaded from cache.", 1.0)
                        return
            except Exception:
                pass

        if progress_callback: progress_callback("🔍 Initializing Pattern Extraction (Pass 0)...", 0.05)
        
        if not os.path.isdir(self.remote2_path):
            if progress_callback: progress_callback("⚠ Reference folder missing. Skipping extraction.", 1.0)
            self._save_cache() # Save empty shell with version
            return

        all_files = []
        for root, dirs, files in os.walk(self.remote2_path):
            if 'backup' in root.lower() or 'temp' in root.lower(): continue
            for file in files:
                if file.endswith('.cfg') or file.endswith('.dat'):
                    all_files.append(os.path.join(root, file))
        
        total = len(all_files)
        if total == 0:
            if progress_callback: progress_callback("✔ No reference files found.", 1.0)
            return

        import time
        for i, path in enumerate(all_files):
            file = os.path.basename(path)
            if progress_callback and (i % 5 == 0):
                progress_callback(f"🛡️ Pass 0: Analyzing {file}...", 0.05 + (0.9 * (i / total)))
            
            self._process_file(file, path)
            
            # [v113.10] IMPORTANT: Yield to GIL on first-load to prevent "Not Responding"
            # This allows the main thread to process Windows events even during heavy CPU/zlib work.
            if i % 10 == 0:
                time.sleep(0.001) 
        
        self._save_cache()
        if progress_callback: progress_callback("✔ Extraction complete. Registry ready.", 1.0)

    def _process_file(self, filename: str, path: str):
        try:
            with open(path, 'rb') as f:
                raw = f.read()
            
            if not raw: return

            # Record Header Patterns
            header = raw[:4]
            self.data["headers"][filename] = header.hex()
            
            # Decompress and Parse
            payload = self._decompress(raw)
            try:
                # Handle possible trailing nulls in SnowRunner files
                text = payload.decode('utf-8', errors='replace').strip()
                if '\x00' in text:
                    text = text.split('\x00')[0]
                
                # Check for JSON structure
                if text.startswith('{'):
                    js_data = json.loads(text)
                    self._extract_json_patterns(filename, js_data)
                else:
                    # Pure binary file (like some fog/sts files)
                    self._extract_binary_patterns(filename, payload)
            except Exception as e:
                # If decompression/decoding fails, still track basic stats
                self.data["schemas"][filename] = {"parsed": False, "error": str(e), "size": len(payload)}

        except Exception as e:
            print(f"[Extractor] Failed to process {filename}: {e}")

    def _extract_json_patterns(self, filename: str, js_data: dict):
        # 1. Global Progress patterns (CompleteSave.cfg)
        if "CompleteSave" in js_data:
            ssl = js_data["CompleteSave"].get("SslValue", {})
            self.data["global_patterns"]["CompleteSave"] = {
                "keys": list(ssl.keys()),
                "upgradesGiverData": list(ssl.get("upgradesGiverData", {}).keys()),
                "watchpoints_list": list(ssl.get("discoveredWatchpoints", {}).keys())
            }
        
        # 2. Regional Logic (sts_level files)
        if filename.startswith("sts_level_"):
            region_id = filename.replace("sts_level_", "").replace(".cfg", "").replace(".dat", "")
            ssl = js_data.get("SslValue", {})
            self.data["region_patterns"][region_id]["sts_keys"] = list(ssl.keys())
            self.data["region_patterns"][region_id]["sts_is_json"] = True

    def _extract_binary_patterns(self, filename: str, payload: bytes):
        # 1. Fog characteristics
        if filename.startswith("fog_level_"):
            region_id = filename.replace("fog_level_", "").replace(".cfg", "").replace(".dat", "")
            # Count unique bytes for "Reveal Map" reference
            unique_bytes = list(set(payload))
            self.data["region_patterns"][region_id]["fog_size"] = len(payload)
            self.data["region_patterns"][region_id]["fog_unique_bytes"] = unique_bytes

    def _save_cache(self):
        with open(self.cache_file, 'w') as f:
            json.dump(self.data, f, indent=2)

if __name__ == "__main__":
    # Test execution
    remote2 = r'e:\Snow Runner New Tool\remote2\remote'
    cache = r'e:\Snow Runner New Tool\app\snowrunner_save_editor_data\reference_patterns.json'
    extractor = ReferenceExtractor(remote2, cache)
    extractor.extract_all()
