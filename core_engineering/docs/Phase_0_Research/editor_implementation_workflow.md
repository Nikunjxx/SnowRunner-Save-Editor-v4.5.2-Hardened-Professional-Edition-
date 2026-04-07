# SnowRunner Save Editor — Master Implementation Workflow

> This document defines the full implementation plan, architecture decisions, known challenges,
> and future-proofing strategy for every functional module of the editor.
> Aesthetics are explicitly out of scope for this document.

---

## OVERVIEW: The App's Core Philosophy

```
LOAD → SCAN → DISPLAY → MODIFY → WRITE → VERIFY
```

Every single feature in the app follows this pipeline in order.
No tab should mutate anything until the **SCAN** phase has passed cleanly.
No write should happen without **VERIFY** confirming the output is valid.

---

## CRITICAL ARCHITECTURE DECISIONS (Gap Fixes & Polishing)

1. **Multi-File Atomic Transactions & Rollbacks**
   No file is ever written directly. If a feature (e.g., Watchtowers) requires updating two files, they are treated as a single transaction:
   - **Start:** Call `create_backup()` to secure the original slot state.
   - **Write:** Write to `CompleteSave.cfg.tmp` AND `CommonSslSave.cfg.tmp`.
   - **Validate:** Load both `.tmp` files through the JSON validator.
   - **Commit:** If validation passes, `os.replace` both temp files to the original filenames.
   - **Rollback:** If validation fails, or if a write throws an exception, the transaction aborts. The `tmp` files are discarded, the backup is automatically restored, and the user is alerted to the aborted state.

2. **Strict FieldAccessor Enforcement**
   **Decision: Direct dictionary access (e.g., `save["money"]`) is strictly forbidden across the entire backend and UI.** Every read/write operation against save data must go through the version-aware `FieldAccessor` class. This prevents silent failures when Saber Interactive changes JSON field names in future DLC updates.

3. **STS Binary Edit Policy (Blocked for Safety)**
   **Decision: ❌ Do not support structural edits.**
   Writing STS binary graphs is too high-risk and will cause world desyncs. Features like completing a bridge or pipeline will be explicitly disabled/greyed out in the UI with a tooltip explaining that structural mechanics are locked to protect the save file.

4. **Registry Source Versioning**
   For Phase 1, the registry is a local file (`data/maprunner_registry.json`) heavily versioned inside the app: `{ "registry_version": "1.0", "compatible_game_build": "33.0" }`. Cloud updates via GitHub are deferred to Phase 3 to avoid blocking initial development with network logic.

5. **Severity Model (Scan Constraints)**
   - `INFO`: Logging only. Proceed safely.
   - `WARNING`: Non-fatal linkage issue (e.g., duplicate IDs). User CAN proceed and edit. Fix available.
   - `ERROR`: Structural issue (Missing base file, bad JSON syntax, zero-byte file). UI tabs **LOCKED DOWN**. App refuses to mutate data.

6. **UI/State Observers (Pub/Sub)**
   A strict Pub/Sub Observer pattern is required. `EditorContext` maintains all state. When `commit()` happens, it issues an event. Every Tkinter Tab must implement `def on_state_updated(self, context)` to automatically repaint itself, guaranteeing no stale UI.

7. **ZLib Caching Strategy**
   STS and FOG files are cached in-memory upon decompiling to prevent the UI from freezing during rapid tab-switching. The `ThreadPoolExecutor` decodes the 1.5MB files perfectly once, and serves the cached array unless the file modification timestamp changes natively.

8. **Fog Write Pipeline & Templating**
   Fog is the **only** binary file we will write.
   **Pipeline:** Extract native binary header → pack new float32 array `[X, Y]` → Zlib compress (Level 6) → concatenate header + payload → overwrite file.
   **Generation:** Arrays will NEVER be generated from scratch. The app will ship with a `data/fog_templates/` directory containing known-working verified coordinate arrays extracted from perfectly revealed 100% save files, mapped region by region.

---

## MODULE 0: Application Bootstrap & File Loading

### 0.1 What It Does
The first screen the user sees. Controls everything that comes after.

**UI Elements:**
- `[📂 Load Save Folder]` button — opens a folder browser
- Beside it: a **dropdown** listing all detected `CompleteSave*.cfg` / `CompleteSave*.dat` files found in the loaded folder
- A large **console panel** below (scrollable, monospace font) showing file scan results
- A **progress bar / spinner** on the scan button (blue, animated) that stays greyed out until a folder is loaded
- `[🔍 Scan Folder]` and `[🛠 Fix All Issues]` buttons at the bottom — disabled (grey) until scan completes

### 0.2 Implementation Steps

**Step A — Folder Browser:**
```python
# Platform detection must happen at load time
def detect_platform(folder_path: str) -> str:
    files = os.listdir(folder_path)
    if any(f.endswith(".cfg") for f in files):
        return "STEAM"   # Steam uses .cfg
    elif any(f.endswith(".dat") for f in files):
        return "EPIC_OR_MS"  # Epic/MS Store uses .dat
    return "UNKNOWN"
```

**Step B — File Discovery & Slot Resolution:**
The folder will contain files for multiple save slots. Your app must resolve them into slot groups:

| Slot | CompleteSave | STS Pattern | FOG Pattern |
|------|-------------|-------------|-------------|
| Slot 1 | `CompleteSave.cfg` | `sts_level_*.cfg` | `fog_level_*.cfg` |
| Slot 2 | `CompleteSave1.cfg` | `1_sts_level_*.cfg` | `1_fog_level_*.cfg` |
| Slot 3 | `CompleteSave2.cfg` | `2_sts_level_*.cfg` | `2_fog_level_*.cfg` |
| Slot 4 | `CompleteSave3.cfg` | `3_sts_level_*.cfg` | `3_fog_level_*.cfg` |

```python
SLOT_PREFIX_MAP = {
    0: "",    # Slot 1: no prefix
    1: "1_",  # Slot 2: prefix "1_"
    2: "2_",  # Slot 3: prefix "2_"
    3: "3_",  # Slot 4: prefix "3_"
}
COMPLETE_SAVE_MAP = {
    0: "CompleteSave.cfg",
    1: "CompleteSave1.cfg",
    2: "CompleteSave2.cfg",
    3: "CompleteSave3.cfg",
}
```

**Step C — Dropdown Population:**
When folder is loaded, scan for all `CompleteSave*.cfg` files → populate the dropdown.
Dropdown label should be human-readable:
`"Slot 1 — Michigan (Last Played: 2h ago)"` ← derive from `gameTime` and `lastLoadedLevel`

**Step D — Slot Selection:**
When user picks a slot from the dropdown:
1. Load that slot's `CompleteSave*.cfg`
2. Filter all other files by that slot's prefix
3. Reload the console to show ONLY that slot's files
4. Refresh all tabs with that slot's data

### 0.3 Challenges

| Challenge | Solution |
|-----------|----------|
| Epic uses `.dat` instead of `.cfg` — same JSON inside | Detect by extension, treat identically at parse level |
| Player may have 1, 2, 3, or 4 active slots | Only show slots that have a `CompleteSave` file present |
| Steam save path varies by user Steam ID | Store last used path in app config; let user re-browse if needed |
| User may point to wrong folder | Validate by checking for `CompleteSave.cfg` OR `CompleteSave.dat` existence |
| Folder may be read-only (Steam Cloud locked) | Check write permission before scan; warn user if read-only |

---

## MODULE 1: File Scanner & Console

### 1.1 What It Does
After folder load, user clicks `[🔍 Scan Folder]`. The app performs a deep integrity scan across all files in the selected slot and displays the results in the console.

### 1.2 Scan Phases

**Phase 1 — File Inventory (fast)**
- List all files found
- Categorise each as: Plaintext JSON / Binary+Zlib / Unknown
- Check null terminator presence on every `.cfg`/`.dat` file
- Console output: `[✅] CompleteSave.cfg — Plaintext JSON, 362KB, null terminator OK`

**Phase 2 — JSON Integrity (medium)**
- Parse all plaintext files
- Verify SSL wrapper structure: `{RootKey: {SslType, SslValue}, cfg_version: 1}`
- Verify required fields exist in `CompleteSave.cfg`
- Console output: `[✅] CompleteSave.cfg — JSON valid, all required fields present`

**Phase 3 — Binary Decompression (slow)**
- For each `sts_level_*.cfg` and `fog_level_*.cfg` in slot:
  - Detect zlib magic bytes (`0x78 0x9C`)
  - Attempt decompression
  - Validate decompressed output is non-zero length
  - Console: `[✅] fog_level_us_01_01.cfg — Decompressed OK (4.2KB)`
  - Or: `[❌] sts_level_ru_04_02.cfg — Zlib error: invalid header`

**Phase 4 — Cross-File Linkage Check (deep)**
- Verify every map ID in `visitedLevels` has a corresponding `sts_level_*.cfg`
- Verify every watchtower ID in `watchPointsData` exists in the registry
- Verify `finishedObjs` contains no duplicate IDs
- Verify `upgradesGiverData` keys match known level IDs
- Console: `[⚠️] watchPointsData has 2 IDs not in registry: RU_99_01_WP_01, ...`

**Phase 5 — Auto-Fix Pass (if "Fix All Issues" is clicked)**
- Deduplicate `finishedObjs`
- Remove orphaned watchtower IDs
- Re-add missing null terminators on plaintext files
- Console: `[🛠] Fixed: removed 3 duplicate entries in finishedObjs`

### 1.3 Console Design Requirements

```
[12:03:01] 📁 Loaded folder: C:\Steam\userdata\12345678\remote
[12:03:01] 🔍 Detected platform: STEAM
[12:03:01] 📊 Found 4 save slots
[12:03:01] ─────────────────────────────────────────────────────
[12:03:02] SLOT 1 FILE SCAN
[12:03:02] ✅ CompleteSave.cfg      — JSON OK    (362KB)
[12:03:02] ✅ CommonSslSave.cfg     — JSON OK     (24KB)
[12:03:02] ✅ GameVersionSave.cfg   — JSON OK     (161B) [SNOW_DLC_17]
[12:03:02] ✅ fog_level_us_01_01    — Binary OK, decompressed 4.1KB
[12:03:02] ✅ sts_level_us_01_01    — Binary OK, decompressed 812KB
[12:03:02] ⚠️ fog_level_ru_17_01   — Stub file (player never visited)
[12:03:02] ─────────────────────────────────────────────────────
[12:03:02] LINKAGE SCAN
[12:03:02] ✅ visitedLevels: 31 maps — all STS files present
[12:03:02] ✅ finishedObjs: 215 entries — no duplicates
[12:03:02] ✅ upgradesGiverData: all keys are valid level IDs
[12:03:02] ─────────────────────────────────────────────────────
[12:03:02] SCAN COMPLETE — 0 errors, 1 warning
```

### 1.4 Challenges

| Challenge | Solution |
|-----------|----------|
| Large STS files (up to 1.5MB) block the UI thread | Run scan in background thread; update console via queue |
| Decompression of unknown binary formats may hang | Set a 5-second timeout per file; skip with `[⚠️ TIMEOUT]` |
| Some fog files are legitimately tiny stubs | Check size < 100 bytes first; mark as `STUB` not `ERROR` |
| Old save slots may reference deprecated level IDs | Registry should contain deprecated IDs with a `deprecated: true` flag |

---

## MODULE 2: Bank & Rank Tab

### 2.1 What It Does
Displays and allows editing of Money, XP, and Rank. All values read from the active slot's `CompleteSave*.cfg`.

### 2.2 Fields & Source Mapping

| UI Label | `CompleteSave.cfg` Field | Type | Safe Range |
|----------|--------------------------|------|------------|
| Money | `money` | int | 0 – 99,999,999 |
| Experience | `experience` | int | 0 – 4,294,967 |
| Rank | Derived from `experience` via XP table | display only | — |
| Game Time | `gameTime` | float (seconds) | Read-only display |
| Hard Mode | `isHardMode` | bool | Toggle |
| Metric System | `metricSystem` | int | 0=Imperial, 1=Metric |

**Rank XP Table:** Reference `https://old.maprunner.info/resources/rank-xp` — bundle this as a static lookup in `core_engineering/data/rank_xp_table.json`

### 2.3 Implementation Pattern
```python
# On slot load — populate fields
money_value = complete_save.get("money", 0)
xp_value    = complete_save.get("experience", 0)
rank        = lookup_rank_from_xp(xp_value, rank_table)  # static lookup

# On Apply — validate then write
def apply_bank_rank(money: int, xp: int) -> bool:
    if not (0 <= money <= 99_999_999):
        show_error("Money must be 0 – 99,999,999")
        return False
    if not (0 <= xp <= 4_294_967):
        show_error("XP out of valid range")
        return False
    complete_save["money"] = money
    complete_save["experience"] = xp
    write_complete_save(complete_save)
    return True
```

### 2.4 Challenges
- **XP/Rank are bidirectional** — if user enters a rank, back-calculate the XP threshold
- **gameTime is displayed only** — editing it mid-game causes no gameplay effect but confuses leaderboards
- **Hard mode flag** — has TWO locations: `isHardMode` (bool) and `gameDifficultyMode` (int). Both must be kept in sync

---

## MODULE 3: Vehicle Tab

Existing functionality. Maintain as-is. Ensure it re-reads from the active slot on slot switch.

**Key fields in `CompleteSave.cfg`:**
- `garagesData` — trucks stored in garages
- `modTruckOnLevels` — mod trucks placed in the world
- `modTruckTypesRefundValues` — refund tracking for removed mods

**Slot-aware rule:** On slot switch, reload `garagesData` from the new slot's `CompleteSave*.cfg`.

---

## MODULE 4: Progression Tab (Read-Only)

### 4.1 What It Does
Displays the player's current real progress. **No mutations.** Pure information display.

### 4.2 Stats to Display

| Stat | Source |
|------|--------|
| Total maps visited | `len(visitedLevels)` |
| Total maps in game | `len(registry["maps"])` |
| Unexplored maps | Total minus visited |
| % complete (maps) | `visited / total * 100` |
| Contracts complete | `count of _OBJ IDs in finishedObjs` |
| Tasks complete | `count of _TSK IDs in finishedObjs` |
| Contests complete | `count of _CNT IDs in finishedObjs` |
| Total objectives | From registry |
| Upgrades collected | From `upgradesGiverData` |
| Watchtowers found | From `watchPointsData` |
| Total co-op sessions | `CommonSslSave.platformStatsInfo.totalCoopSessions` |
| Total distance (km) | `CommonSslSave.platformStatsInfo.totalDistanceMeters / 1000` |
| Total money earned | `CommonSslSave.platformStatsInfo.totalMoneyEarned` |
| DLC Season level | From `GameVersionSave.stream` |

### 4.3 Challenges
- `visitedLevels` may contain IDs the registry doesn't know (future DLC not yet in registry)  
  → Display unknown IDs in a separate section: "Unknown Maps (future DLC?)"
- Distance is lifetime (all slots combined) — must clarify this in UI

---

## MODULE 5: Objectives Tab

### 5.1 What It Does
Shows all Tasks, Contracts, and Contests from every map. User can filter, select, accept, or complete them.

### 5.2 UI Controls

- **Filter: Region** — dropdown (All / Michigan / Alaska / Taymyr / …)
- **Filter: Map** — dropdown cascaded from Region selection
- **Filter: Type** — dropdown (All / Task / Contract / Contest)
- **Filter: Status** — dropdown (All / Completed / Active / Undiscovered)
- **[☑ Select All]** / **[☐ Deselect All]** buttons
- Scrollable list with a checkbox per objective row
- Each row shows: `[☐] Map Name | Company | Objective Name | Type | Status`
- **Bottom bar:** `[Accept Task]` and `[Complete Task]` buttons

### 5.3 Accept vs Complete Logic

```python
def accept_objective(obj_id: str, save: dict) -> dict:
    """
    Accept = move to objectiveStates as isFinished:false.
    Does NOT set cargo counts or stage states.
    The game will be told the task is active.
    SAFE for all types.
    """
    obj_states = save.get("objectiveStates", {})
    if obj_id not in obj_states:
        obj_states[obj_id] = {"isFinished": False, "stagesState": []}
    save["objectiveStates"] = obj_states
    return save

def complete_objective(obj_id: str, save: dict, registry: dict) -> dict:
    """
    Complete = add to finishedObjs, remove from objectiveStates.
    BLOCKS if objective is structural (requires binary STS change).
    """
    if is_structural(obj_id, registry):
        raise BlockedMutation(
            f"'{obj_id}' alters a physical world object (bridge/building). "
            f"Use the STS editor for this (not yet implemented)."
        )
    finished = list(save.get("finishedObjs", []))
    if obj_id not in finished:
        finished.append(obj_id)
    obj_states = dict(save.get("objectiveStates", {}))
    obj_states.pop(obj_id, None)
    save["finishedObjs"] = finished
    save["objectiveStates"] = obj_states
    return save
```

### 5.4 Challenges

| Challenge | Solution |
|-----------|----------|
| ~800+ objectives in total game — UI can't list them all at once | Use virtual scrolling / lazy rendering |
| Structural objectives (bridge, pipeline) cannot be safely auto-completed | Mark with `⚠️ STRUCTURAL` badge; block and explain why |
| Accepting tasks that have prerequisites not met | Check `discoveredObjectives` — only accept if discovered OR explicitly bypass with warning |
| Batch-completing contests requires scoring data | For contests: only add to `finishedObjs`, do not attempt to inject score data |

---

## MODULE 6: Region Tab

### 6.1 What It Does
Unlock things at a regional or map level. Operates on filtered sets of data.

### 6.2 UI Layout

```
[ ] Michigan, USA             [ ] Alaska, USA
[ ] Taymyr, Russia            [ ] Kola Peninsula (S1 DLC)
[ ] Yukon (S2 DLC)            [ ] Wisconsin (S3 DLC)
... (all 20 regions)

[Unlock All Maps in Selected Regions]
[Unlock & Discover All Trucks & Trailers]
[Unlock All Watchtowers]
[Unlock All Garages]
[Full Upgrade All Garages]
```

### 6.3 Implementation Per Button

**Unlock All Maps:**
```python
# For each map in selected regions, add level_id to visitedLevels
# AND set levelGarageStatuses[level_id] = 2 (garage open)
# AND add level_id to any gateway linkage arrays
def unlock_map(level_id: str, save: dict) -> dict:
    visited = list(save.get("visitedLevels", []))
    if level_id not in visited:
        visited.append(level_id)
    save["visitedLevels"] = visited

    garages = dict(save.get("levelGarageStatuses", {}))
    garages[level_id] = 2
    save["levelGarageStatuses"] = garages
    return save
```

**Unlock Watchtowers:**
```python
# Must update BOTH CompleteSave.cfg AND CommonSslSave.cfg
# See Watchtower Safety Rule from linkage guide
def unlock_all_watchtowers_for_region(
    region_maps: list[str], complete_save: dict, common_ssl: dict, registry: dict
) -> tuple[dict, dict]:
    for tower_id, meta in registry["watchtowers"].items():
        if meta["map_id"] in region_maps:
            complete_save, common_ssl = unlock_watchtower_safe(
                tower_id, complete_save, common_ssl, registry
            )
    return complete_save, common_ssl
```

**Unlock Garages:**
```python
def unlock_garages_for_region(region_maps: list[str], save: dict) -> dict:
    garages = dict(save.get("levelGarageStatuses", {}))
    for level_id in region_maps:
        garages[level_id] = 2
    save["levelGarageStatuses"] = garages
    return save
```

**Discover Trucks & Trailers:**
```python
# Trucks found in the world are tracked in garagesData
# World-spawn trucks are in sts_level (binary) → cannot discover without STS write
# SAFE alternative: add truck to garagesData in a "discovered but not owned" state
# OR only mark as recoverable (show in game's recovery list)
```

> [!WARNING]
> **Truck discovery linkage is complex.** Trucks found in the world have their discovery state in `sts_level_*.cfg` (binary). Adding them purely via `CompleteSave` will make them appear in the garage but not mark them as "discovered in the world." The safest approach is to only offer "Add to Garage" (plaintext) and disclaim that world-spawn state is separate.

### 6.4 Challenges

| Challenge | Solution |
|-----------|----------|
| DLC regions — user may not own the DLC | Check `visitedLevels` for any map in that region before enabling unlock; warn if never visited |
| Unlocking maps that were never generated yet (no STS file) | The game will generate STS on first visit — this is safe. Just add to `visitedLevels`. |
| Watchtowers need dual-file write | Always call the paired function, never write to just one file |
| Garage full-upgrade state is stored differently per-season | Season 5+ garages have expanded garage modules — validate garage IDs against registry |

---

## MODULE 7: Upgrades Tab

### 7.1 What It Does
Show all hidden world upgrades. Filter by region/map. Let user select and unlock them.

### 7.2 UI Layout

```
Filter Region: [Michigan ▼]     Filter Map: [Black River ▼]
[☑ Select All]    [☐ Deselect All]

[ ] Si-6V/2100T Engine       — Black River — Engine
[ ] AAT-8V 5.2 Custom        — Black River — Transmission
[ ] SnowRunner Tires         — Black River — Tires
[ ] Engageable AWD           — Black River — Transfer Case
...

[🔓 Unlock Selected Upgrades]
```

### 7.3 Implementation

```python
def unlock_selected_upgrades(upgrade_ids: list[str], save: dict, registry: dict) -> dict:
    """
    Sets each upgrade to collected state in upgradesGiverData.
    Groups by level_id to avoid overwriting unrelated upgrades on the same map.
    """
    upgrades_giver = dict(save.get("upgradesGiverData", {}))

    for upg_id in upgrade_ids:
        meta = registry["upgrades"].get(upg_id)
        if not meta:
            continue  # Unknown ID — skip silently
        level_id = meta["map_id"]
        if level_id not in upgrades_giver:
            upgrades_giver[level_id] = {}
        upgrades_giver[level_id][upg_id] = 2  # 2 = collected

    save["upgradesGiverData"] = upgrades_giver
    return save
```

### 7.4 Challenges
- **Upgrade IDs are inconsistent** (some named, some numbered — see linkage guide §7.5)
- **Not all upgrades are in the registry** — DLC upgrades may be missing from older registry versions
- **Partial unlock** — user may want only specific upgrade types (engine only, no tires) → add type filter

---

## MODULE 8: Trials, Awards, PROS, Rules Tabs

Keep the existing implementation. Ensure:
- `finishedTrials` is read from `CommonSslSave.cfg` (not `CompleteSave.cfg`)
- Achievement state uses `CommonSslSave.achievementStates`
- PROS data uses `CommonSslSave.givenProsEntitlements` and `givenProsBanners`
- All modifications write back to **`CommonSslSave.cfg`** not `CompleteSave.cfg`

This is the most common mistake — writing achievements to the wrong file.

---

## MODULE 9: Time Tab

### 9.1 What It Does
Control game time parameters: time of day, time speed multiplier, weather.

### 9.2 Fields & Source
These are stored in `CompleteSave.cfg` under `SslValue`:

| UI Control | Field Name | Type | Range |
|-----------|-----------|------|-------|
| Time of Day | `dayTime` or `gameTime` sub-field | float | 0.0–24.0 (hours) |
| Time Speed | `timeScale` or `dayDuration` | float | 0.1x – 10.0x |
| Weather | `weather` or `weatherState` | string/int | rain / clear / fog |
| Season | `season` | string | winter / summer / etc |

> [!WARNING]
> **Time fields are DLC-season-dependent.** Season 8+ (Belozersk Glades) introduced farming seasons which changes the field schema. Always verify the field exists before setting it. If `dayTime` doesn't exist in the save, do not create it blindly.

### 9.3 Implementation
```python
def set_time_of_day(hour: float, save: dict) -> dict:
    """Hour: 0.0=midnight, 6.0=dawn, 12.0=noon, 18.0=evening"""
    if "dayTime" in save:
        save["dayTime"] = max(0.0, min(24.0, hour))
    elif "globalTime" in save:
        save["globalTime"] = hour * 3600  # convert to seconds
    else:
        # Field doesn't exist in this save — inform user, don't inject
        raise FieldNotFound("Time field not found in this save slot's version")
    return save
```

### 9.4 Challenges
- Time field name changed across game versions — need a field-detection fallback
- Weather state is map-specific in some versions (global override may not work)
- Farming season (Season 8) has its own time system — separate from world time

---

## MODULE 10: Game Stats Tab

### 10.1 What It Does
Read-only display of all tracked stats. No mutations.

### 10.2 Data Sources

| Stat | Source File | Field Path |
|------|-------------|------------|
| Total money earned | `CommonSslSave.cfg` | `platformStatsInfo.totalMoneyEarned` |
| Total distance (m) | `CommonSslSave.cfg` | `platformStatsInfo.totalDistanceMeters` |
| Total co-op sessions | `CommonSslSave.cfg` | `platformStatsInfo.totalCoopSessions` |
| Achievement count | `CommonSslSave.cfg` | `count of achievementStates where isUnlocked: true` |
| Save slot history | `CommonSslSave.cfg` | `saveSlotsTransaction` (parse FILETIME hex) |
| Trucks owned | `CompleteSave.cfg` | `garagesData` count |
| Contracts done | `CompleteSave.cfg` | `finishedObjs` filtered by `_OBJ` |
| Tasks done | `CompleteSave.cfg` | `finishedObjs` filtered by `_TSK` |
| Contested won | `CompleteSave.cfg` | `finishedObjs` filtered by `_CNT` |

**FILETIME Conversion:**
```python
def filetime_hex_to_datetime(hex_str: str) -> str:
    """Convert Saber FILETIME hex to human-readable date"""
    # e.g., "0x0000017e0ad96758"
    filetime_int = int(hex_str, 16)
    # FILETIME = 100ns intervals since Jan 1 1601
    EPOCH_DIFF = 116444736000000000  # 100ns between 1601 and 1970
    unix_timestamp = (filetime_int - EPOCH_DIFF) / 10_000_000
    from datetime import datetime, timezone
    return datetime.fromtimestamp(unix_timestamp, tz=timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
```

---

## MODULE 11: Fog Tools Tab

### 11.1 What It Does
Manual fog editor. Lets user reveal sections of a map's fog of war.

### 11.2 Fog File Availability Logic

```
User loads folder
    ↓
App scans for fog files matching current slot prefix
    ↓
Slot 1: fog_level_*.cfg
Slot 2: 1_fog_level_*.cfg
    ↓
Filter: only show files that exist AND are non-stub (>100 bytes)
    ↓
Dropdown shows USER-FRIENDLY names:
    "fog_level_us_01_01.cfg" → "Michigan — Black River"
    "1_fog_level_ru_08_03.cfg" → "[Slot 2] Belozersk Glades — Heartlands"
```

### 11.3 Human-Friendly Name Mapping

This mapping must be built from the registry — **never hardcoded:**

```python
def get_fog_display_name(filename: str, registry: dict) -> str:
    """
    Converts fog filename to human display name.
    fog_level_us_01_01.cfg → "Michigan — Black River"
    1_fog_level_ru_08_03.cfg → "[Slot 2] Belozersk Glades — Heartlands"
    """
    # Strip slot prefix if present
    slot_label = ""
    f = filename
    for slot_num in ["3_", "2_", "1_"]:
        if f.startswith(slot_num):
            slot_label = f"[Slot {int(slot_num[0]) + 1}] "
            f = f[len(slot_num):]
            break

    # Strip "fog_level_" and ".cfg"/".dat"
    level_id = f.replace("fog_level_", "").replace(".cfg", "").replace(".dat", "")
    # e.g., "us_01_01" → "level_us_01_01"
    full_level_id = f"level_{level_id}"

    meta = registry["maps"].get(full_level_id, {})
    region = meta.get("region", "Unknown Region")
    name   = meta.get("human_name", level_id)

    return f"{slot_label}{region} — {name}"
```

### 11.4 Fog Reveal/Write Pipeline

```
User selects a fog file from dropdown
    ↓
App decompresses it (zlib)
    ↓
App displays current revealed state (coordinate grid overlay on map thumbnail)
    ↓
User clicks "Reveal Full Map"
    ↓
App generates a full-coverage coordinate array for that map
    ↓
App zlib-compresses the new array
    ↓
App reconstructs the binary file (header + compressed payload)
    ↓
App writes back the file WITH null terminator preserved
    ↓
App re-scans the file to confirm round-trip success
```

### 11.5 Challenges

| Challenge | Solution |
|-----------|----------|
| Fog files don't exist for maps never visited | Warn user: "This map has never been visited. Fog file will be generated on first visit in-game. Cannot pre-reveal." |
| Fog coordinate format is not fully documented | Use known working coordinate arrays from existing saves as templates. Never generate from scratch — copy and scale. |
| After reveal, game may regenerate fog on visit | Full reveal should add entire map bounds — game respects pre-revealed cells. Partial reveals may get overwritten. |
| Fog files for `.dat` (Epic) need same treatment | Identical format — just different extension. Same pipeline. |
| Binary write must perfectly replicate Saber header | Copy the original header bytes unchanged. Only replace the zlib payload block. |

```python
def rewrite_fog_file(original_path: pathlib.Path, new_fog_zones: list[dict]):
    """
    Writes new fog reveal data back to a binary fog file.
    Preserves the original Saber header exactly.
    """
    raw = original_path.read_bytes()
    zlib_start = raw.find(b"\x78\x9c")
    header = raw[:zlib_start]  # Preserve original header exactly

    # Pack new coordinate array
    import struct, zlib
    payload = b""
    for zone in new_fog_zones:
        payload += struct.pack("<ff", zone["x"], zone["y"])

    compressed = zlib.compress(payload, level=6)  # Use level 6 (Saber default)
    new_file = header + compressed  # No null terminator for binary files

    original_path.write_bytes(new_file)
```

---

## ARCHITECTURE: Future-Proofing Strategy

### Problem 1: New DLC Seasons Will Break the Registry
**Solution:** Registry is versioned. App ships with a `registry_version` field. On launch, check a remote registry endpoint (optional — the app works offline too). Show a banner: `"Registry v12 loaded. Season 17 maps may be incomplete. [Update Registry]"`.

### Problem 2: Game Updates May Change Field Names
**Solution:** All field access goes through a `FieldAccessor` class with fallback chains:
```python
class FieldAccessor:
    def get_money(self, save: dict) -> int:
        return save.get("money") or save.get("playerMoney") or 0
```
Never access `save["money"]` directly in any UI or mutation code.

### Problem 3: Platform Differences (Steam / Epic / MS Store / Console)
**Solution:** Platform is detected once at load time and stored in `AppContext.platform`. All file read/write calls go through a `PlatformAdapter` that handles extension differences.

### Problem 4: The Editor Catches Up With a New Save Format
**Solution:** `GameVersionSave.cfg` contains `changeList` (build number). If the app detects a `changeList` higher than its tested version, show a **warning banner**: `"This save was created on game build #831755. Editor was tested on #810000. Proceed with caution."` Never block the user — just inform.

### Problem 5: Partial Write = Save Corruption
**Solution:** All writes use an atomic pattern:
```
1. Write to a temp file (e.g., CompleteSave.cfg.tmp)
2. Verify the temp file is valid JSON + null terminated
3. Rename the original to .bak
4. Rename the temp file to the original name
5. Only then delete the .bak
```
If step 3 fails, the original is untouched.

### Problem 6: Second Developer Joins the Project
**Solution:** The 3 documents (`save_architecture_db_schema.md`, `editor_linkage_engineering_guide.md`, this workflow) form a complete onboarding kit. No institutional knowledge is locked in one person's head.

---

## IMPLEMENTATION ORDER (Recommended)

```
Phase 1 — Foundation (do first, everything depends on this)
  ✅ SlotResolver — maps file prefixes to slot numbers
  ✅ SaveLoader — loads all plaintext files with null byte validation
  ✅ BinaryDecoder — decompresses STS and FOG files
  ✅ Registry — builds the MapRunner static lookup table

Phase 2 — Core UI Shell
  ✅ Load Folder button + folder browser
  ✅ Slot dropdown
  ✅ Console panel with background thread scanning
  ✅ Scan + Fix buttons (disabled state logic)

Phase 3 — Read Tabs (no mutations, build linkages first)
  ✅ Progression tab (read-only stats)
  ✅ Game Stats tab (read-only lifetime data)
  ✅ Bank & Rank display (read before write)

Phase 4 — Write Tabs (mutations, in safe order)
  ✅ Bank & Rank (simplest — single file, no linkage)
  ✅ Upgrades (medium — needs registry join)
  ✅ Objectives (complex — TSK/OBJ/CNT distinction, structural guard)
  ✅ Region Unlock (complex — dual-file for watchtowers)

Phase 5 — Advanced Tabs
  ✅ Fog Tools (binary read/write, high risk)
  ✅ Time Tab (field-version-aware)
  ✅ Trials / Awards / PROS (CommonSslSave writer)

Phase 6 — Polish
  ✅ Backup-on-write everywhere
  ✅ Atomic write pattern everywhere
  ✅ Registry versioning + update check
  ✅ Full slot-switch refresh on all tabs
```

---

## KNOWN HARDEST CHALLENGES (Research Required Before Starting)

| Risk | Details | Mitigation |
|------|---------|------------|
| 🔴 **STS binary writer** | Writing back to `sts_level_*.cfg` requires perfectly reproducing Saber's binary struct layout. One wrong byte = crash on load. | Implement STS as **read-only** in Phase 1-5. Only add STS write in Phase 6 after full test coverage. |
| 🔴 **Fog coordinate system** | The coordinate space of fog reveals is not publicly documented. Wrong coordinates = invisible reveal in-game. | Test with known fog files from a fully-revealed save. Extract working coordinates as templates. |
| 🟡 **CommonSslSave dual-write** | Watchtower + achievement data spans two files. Missing either write leaves the save in a halfway state. | Always wrap in a transaction: prepare both mutations, then write both in sequence. If second write fails, roll back the first. |
| 🟡 **Structural objectives** | Bridge/pipeline completion requires a binary STS mutation that we can't safely do yet. | Block these mutations explicitly with a clear user-facing message. |
| 🟡 **DLC gating** | Writing DLC content for unowned DLC causes undefined game behaviour. | Always check `visitedLevels` for sibling maps before allowing any DLC unlock. |
| 🟢 **Registry staleness** | New Season 18 content won't be in the bundled registry. | Version the registry. Allow manual registry update from a hosted file. |
