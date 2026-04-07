# [PH4-PROD-RES] Resource Path Utility for Bundled Assets
import os
import sys

def resource_path(relative_path: str) -> str:
    """Get absolute path to resource, works for dev and for PyInstaller."""
    try:
        # PyInstaller creates a temp folder and stores path in _MEIPASS
        base_path = sys._MEIPASS
    except Exception:
        # In dev mode, use the project root (dir containing 'core_engineering')
        # We derive this from the location of this file
        current_file_dir = os.path.dirname(os.path.abspath(__file__))
        # resource_utils.py is in core_engineering/utils/, so project root is 2 levels up
        base_path = os.path.abspath(os.path.join(current_file_dir, "..", ".."))

    return os.path.join(base_path, relative_path)
