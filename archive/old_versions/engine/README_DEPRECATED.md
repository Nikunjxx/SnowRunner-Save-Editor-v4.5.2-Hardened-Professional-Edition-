# DEPRECATED ENGINE FILES

> [!CAUTION]
> **This directory is DEPRECATED as of v111.00 (2026-04-03).**

## Historical Context
These files represent the legacy synchronous engine architecture of the SnowRunner Save Editor. 

- **Replacement**: All core logic has been refactored into the [integrity_engine/](../../../integrity_engine/) plugin-based architecture.
- **Reason for Archival**: To reduce project clutter, improve build performance, and prevent accidental imports of stale logic.
- **Status**: No files in this directory are imported by the current runtime (`snowrunner_editor.py`).

## File Inventory
- `backups.py` (Legacy)
- `executor.py` (Legacy)
- `integrity_manager.py` (Legacy)
- `resolver.py` (Legacy)
- `validator.py` (Legacy)
