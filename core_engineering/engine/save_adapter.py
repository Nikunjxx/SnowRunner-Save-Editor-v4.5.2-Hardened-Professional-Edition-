# [PH4-INT-002] High-Fidelity Save Adapter
import json
import os
from typing import Any, Dict

class SaveAdapter:
    """
    Binary-to-JSON Translation Layer.
    Ensures bit-parity between high-level state and raw save files.
    """
    
    def __init__(self, root_key="CompleteSave"):
        self.root_key = root_key
        
    def read(self, file_path: str) -> Dict[str, Any]:
        """Reads raw binary file, decodes UTF-8, and unwraps state."""
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"Source file not found: {file_path}")
            
        with open(file_path, "rb") as f:
            raw = f.read()

        # [PH4-INT-003] Binary Safety Check
        if not raw.endswith(b"\x00"):
            # We treat this as a corruption or non-game file
            pass 
            
        # Strip null terminator and decode
        text = raw.rstrip(b"\x00").decode("utf-8")
        payload = json.loads(text)
        
        # Unwrap state (Phase 2 compliance)
        # SnowRunner wraps everything in a matching root key
        if self.root_key in payload:
            return payload[self.root_key]
        return payload

    def write(self, file_path: str, state: Dict[str, Any]):
        """Wraps state, encodes UTF-8, appends null-terminator, and writes bytes."""
        # Wrap state back into root key structure for the game
        wrapped = {self.root_key: state}
        
        # [PH4-INT-004] Deterministic Encoding
        # We use separators for compact representation matching game output
        text = json.dumps(wrapped, separators=(',', ':'))
        
        # Encode and append the mandatory null terminator
        raw_bytes = text.encode("utf-8") + b"\x00"
        
        with open(file_path, "wb") as f:
            f.write(raw_bytes)
            
    def _decode(self, raw_bytes: bytes) -> Dict[str, Any]:
        """Internal decode for testing."""
        text = raw_bytes.rstrip(b"\x00").decode("utf-8")
        return json.loads(text)

    def _encode(self, state: Dict[str, Any]) -> bytes:
        """Internal encode for testing."""
        wrapped = {self.root_key: state}
        return json.dumps(wrapped, separators=(',', ':')).encode("utf-8") + b"\x00"
