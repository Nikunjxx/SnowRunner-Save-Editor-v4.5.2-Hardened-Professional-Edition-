# Architecture & Feature Suggestions: Taking It to the Next Level

While our newly established Master Implementation Workflow covers the *how* of building the editor to be stable and functional, this document outlines high-level technical and UX suggestions to elevate the app from a "working tool" to a **professional-grade, future-proof software application**.

These are recommendations that you should consider integrating into our rebuild roadmap.

---

## 1. Smart Backup Rotation (Data Management)

**The Problem:** Your current `backups.py` logic successfully prevents save corruption by making a backup on every edit. However, if a user uses the tool 100 times, their `SnowRunner/remote/` folder will bloat by hundreds of megabytes with folders named `backup_20260406_...`, potentially angering users with low disk space.
**The Solution:** Implement a **Rotating Backup Manager**.
*   Keep the most recent 10 backups.
*   Keep 1 backup per day for the last 7 days.
*   Keep 1 backup per week for the last month.
*   Auto-delete anything older gracefully.
*   Add a "Manage Backups" tab in the UI where users can see disk space used and one-click "Purge Old Backups".

## 2. Dynamic Registry Auto-Updates

**The Problem:** When Season 18 (or 19/20) releases, new maps, objectives, and upgrades will appear. If the map definitions (`maprunner_registry.json`) are hardcoded inside the `.exe`, you have to recompile and release a whole new version of the app just to add a few map names.
**The Solution:** 
*   Host the `maprunner_registry.json` on a public GitHub repository (or GitHub Gist).
*   On application launch, run a 2-second background network check. If the cloud version is higher than the local internal version, download and cache the new JSON. 
*   This makes the app **permanently forward-compatible** without forcing users to re-download the main `.exe`.

## 3. Telemetry & "Export Debug Log" (Supportability)

**The Problem:** When an end-user downloads your `.exe` from GitHub and it crashes, they will open a vague GitHub Issue saying "It doesn't work." You will have no idea why because you can't see their highly specific, corrupted save file.
**The Solution:** 
*   Implement a robust Python `logging` module that writes exclusively to an `app.log` file in the `%APPDATA%` folder.
*   Add a **"Help & Support"** tab with a large button: `[Generate Diagnostic Package]`.
*   Clicking this zips their `CompleteSave.cfg`, the `app.log`, and the `app_crash.trace` into a single desktop file (`SnowRunner_Debug_Pack.zip`) that they can attach to a Discord message or GitHub issue.

## 4. True Asynchronous UI (Zero Freezes)

**The Problem:** Python Tkinter runs on a single thread. If you decompress a 1.5MB `sts_level` file or run a deep linkage scan, the UI will "freeze" and say "(Not Responding)" in the Windows title bar.
**The Solution:** 
*   Implement a strict `TaskQueue` architecture. 
*   The UI thread ONLY draws buttons and progress bars.
*   A persistent background `ThreadPoolExecutor` processes all reads/writes. They communicate via `queue.Queue()`. 
*   This gives the app a buttery-smooth, premium feel, even when scanning 4 slots and 50 FOG files at once.

## 5. Pydantic Static Typing (Code Safety)

**The Problem:** Reading `save.get("money", 0)` or `save["objectiveStates"]` throughout the codebase is prone to typos. A single misspelled string key (`"objectiveState"` instead of `"objectiveStates"`) causes a silent failure during writing.
**The Solution:** 
*   Use the Python library **`pydantic`**. 
*   We map `CompleteSave.cfg` directly to Python Classes internally.
*   Example: `slot.money = 500000` automatically validates it's an integer, clamps it to the max value, and serializes perfectly back to JSON. If the save file structure changes in a future game update, Pydantic throws a structured schema warning instead of a fatal crash.

## 6. The "Clean Up My Save" Feature (Save Sanitization)

**The Problem:** Over hundreds of hours, SnowRunner saves accumulate "ghost data." Trucks that fell through the world to `-9000` Y-coordinates, cargo duplicated under the map, or multiplayer sessions leaving infinite disconnected trailer stubs. This causes game lag and save bloat (like the "1.5MB STS file" issue).
**The Solution:**
Our Deep Scanner (Module 1) should offer a **"Deep Clean"** option that:
*   Deletes unattached dynamic cargo that is physically out of bounds (Y < -100).
*   Forcibly un-freezes multiplayer trailers that glitched.
*   Removes registry entries for Mod Trucks the user uninstalled months ago (which bloat the `modTruckTypesRefundValues` array).
*   *This alone would make the editor highly sought-after by the community.*

## 7. A Single, Unified CI/CD Build Pipeline

**The Problem:** Your root folder has 17 different `SnowRunner_Editor_v115_07_PLATINUM_FINAL_HOTFIX.spec` files. You are manually running PyInstaller commands, which is messy and prone to missing data files.
**The Solution:** 
*   Delete all `.spec` files.
*   Create one `build.py` script.
*   When you run `python build.py`, it automatically cleans the workspace, bumps the version number in the UI, packages the `.exe` with the exact icon, zips it, and places it in a clean `release/` folder ready for GitHub.

## 8. Pub/Sub UI State Management

**The Problem:** If Tab A updates the player's Money, Tab B (which might show Net Worth) doesn't know about it unless they are tightly coupled, which causes spaghetti code.
**The Solution:** 
*   Implement a simple Event Bus (Publisher/Subscriber).
*   When User edits money, the backend emits `EVENT_SAVE_MUTATED`.
*   Every open UI tab subscribes to that event and cleanly refreshes its own fields automatically. 

---

### Summary of Priority

If I had to rank these on what provides the most value immediately for the rebuild:
1.  **Asynchronous UI:** (Crucial — nothing feels cheaper than a freezing UI).
2.  **Debug Package Exporter:** (Crucial — you will go crazy trying to provide tech support without it).
3.  **Single Build Script:** (Crucial — stops the root folder clutter).
4.  **Rotating Backups:** (Polite to the user's hard drive). 
5.  **Dynamic Registry:** (Highly recommended for long-term survival).
