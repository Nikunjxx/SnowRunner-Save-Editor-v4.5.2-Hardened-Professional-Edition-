# Codebase Analysis & Rebuild Strategy

Based on a deep analysis of your current working directory (`Snow Runner New Tool`) and the four backup directories (`backup`, `backup 2`, `backup_final`, `backup_final2`), I have evaluated all the coding you have done so far. 

Because the previous agent tangled the UI and caused regressions (likely by modifying the monolithic `snowrunner_editor.py` incorrectly), we have a massive 1MB+ file that is too brittle to maintain. 

This document outlines **what we keep, what we rebuild, and what we must add** to achieve the reliable, modular architecture defined in the Master Implementation Workflow.

---

## 1. What is PERFECT (The Keepers)
You have built some incredibly strong backend foundations. These will be salvaged and placed directly into our new `core_engineering` folder:

*   **The Integrity Engine (`integrity_engine/`):** 
    Your concept of `manager.py`, `procedural_mutators.py`, `dependency_resolver.py`, and `validator.py` is excellent. The plugin system (`plugins/`) for isolating mutation logic (e.g., `objectives_plugin.py`) was the right architectural choice. We will keep this logic but strict-type it and ensure it adheres to the new "Join Engine" data model.
*   **The Backup System (`backups.py`):** 
    Your automatic creation of `integrity_backups/` before mutations is a lifesaver. We keep this exactly as is.
*   **Objective Database (`data/objective_database.py`):**
    You already extracted 18KB of raw objective data. This saves us massive amounts of time. We will transform this into the new static MapRunner JSON registry.
*   **I/O Parsers (`io/parser.py`):**
    Your basic JSON loading structure is good. We just need to upgrade it to detect and enforce the `\x00` null byte.

---

## 2. What Needs COMPLETE REBUILD (The Messes)

*   **The Monolith (`snowrunner_editor.py` - All versions):**
    This file is over 1 Megabyte (`1,052,099 bytes`) in almost every backup. It contains UI definitions, file loading, state management, and business logic all crammed into one place. This is why the UI kept breaking. **We are throwing this monolith away.** Standard Tkinter apps should have a `main.py` that is ~200 lines long, which simply loads tabs from the `ui/` folder.
*   **The UI Tabs (`ui/tabs/*.py`):**
    While you started breaking the UI into tabs (`dashboard.py`, `map_unlock.py`, etc.), they are currently deeply coupled with backend mutations. We will rewrite these tabs to be "Dumb UI". This means the UI tab only contains buttons and text—when a button is clicked, it sends a command to the `EditorContext` (Backend), and the Backend does the actual file writing.
*   **Time & Weather Tab:**
    The older code attempts to modify time generically. As discovered, Season 8+ changed the time variable structures for farming. We must rebuild this tab with version-aware field getters.

---

## 3. What is ENTIRELY MISSING (The New Requirements)

To fulfill your new "Systematic Workflow" (Load → Scan → Display → Modify), we must build the following components from scratch that do not exist currently in any backup:

### A. The Folder & Slot Resolver (Module 0)
Your current codebase largely hardcodes `CompleteSave.cfg`. 
*   **Missing:** We need a robust `SlotContext` class that reads the folder, detects `CompleteSave1.cfg` (Slot 2), and automatically maps `1_sts_...` and `1_fog_...` to that slot.
*   **Missing:** Platform detection (`.cfg` vs `.dat`).

### B. The Deep Integrity Console (Module 1)
*   **Missing:** The animated loading screen and scan console you requested. 
*   **Missing:** The 5-phase scan logic. We need a background thread that scans JSON boundaries, decompress-tests Zlib binary files, checks level linkages, and outputs everything block by block to a monospace UI console before unlocking the "Fix Issues" button.

### C. The Dual-Write Transaction System
*   **Missing:** As discovered in the linkage analysis, Watchtowers and Objectives must write to both `CompleteSave.cfg` **and** `CommonSslSave.cfg`. The previous code likely only updated `CompleteSave.cfg`, leaving the game internally desynced (achievements vs actual world state). We need a transactional writer.

### D. The MapRunner Linkage Registry
*   **Missing:** A master `maprunner_registry.json` combining Regions, Maps, Objectives, Watchtowers, and Upgrades into a single source of truth. We will generate this by combining your `objective_database.py` with our new MapRunner findings.

### E. Zlib Binary Decoder & FOG Writer (Module 11)
*   **Missing:** While you have some binary exploration scripts in `archive/`, there is no stable, UI-integrated Fog writer. We need a robust `zlib` stream compressor that preserves the Saber interactive header perfectly so we don't corrupt the `.cfg` binaries.

---

## 4. The Step-by-Step Rebuild Execution Plan

We will start fresh. Your `E:\Snow Runner New Tool` folder will become the definitive version. We will work **backend completely first**, then **UI second**.

**PHASE 1: Backend Foundation (No UI)**
1.  Clean up the root folder. Move the massive `snowrunner_editor.py` pieces into an `archive`.
2.  Establish `core_engineering/data/maprunner_registry.json`.
3.  Build `core_engineering/engine/save_loader.py` (Handles null-bytes, `.dat`/`.cfg`, and Slot awareness).
4.  Build `core_engineering/engine/binary_decoder.py` (Safely reads FOG/STS files without breaking them).
5.  Build the central `EditorContext` class which acts as the brain.

**PHASE 2: The Scanner UI**
1.  Build the pure Tkinter layout for the Load Screen (Dropdown for slots, progress bar, Console window, Scan & Fix buttons).
2.  Connect the UI to the `EditorContext` to perform the 5-phase background scan. 

**PHASE 3: Rebuilding the Tabs (Systematic)**
Instead of dumping all tabs in at once, we will add them one by one, ensuring the backend supports them securely:
1.  **Bank & Rank & Time:** Easy JSON mutations.
2.  **Progression & Game Stats:** Read-only data joins.
3.  **Vehicles:** Repurpose your existing vehicle adapter logic.
4.  **Objectives & Upgrades:** Complex list filtering & MapRunner linkages.
5.  **Region Unlocks:** Implementing the dual-write Watchtower logic.
6.  **Fog Tools:** Implementing the binary FOG injection logic.

By isolating the backend logic from the Tkinter UI, the agent won't be able to "mess up your UI" when fixing a database bug, and vice-versa. Everything will communicate through a strict contract.
