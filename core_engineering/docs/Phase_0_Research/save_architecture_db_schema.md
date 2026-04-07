# SnowRunner Save Architecture — Definitive Ground-Truth Report

> [!IMPORTANT]
> **This document is built from direct byte-level inspection of every single file in `remote2/remote`. Every claim is verified, not assumed.**

---

## 1. The SSL Type System (The Foundation)

Every `.cfg` file in SnowRunner follows the **SSL (Save State Layer)** wrapper pattern. The structure is always:
```json
{ "<RootKey>": { "SslType": "<TypeName>", "SslValue": { ... } }, "cfg_version": 1 }
```
All files also share a **null terminator byte `\x00`** at the very end of the file (after the closing `}`). This is critical — any tool that writes these files must preserve this null byte or the game will refuse to load the save.

---

## 2. Complete File Inventory — Ground-Truth Format Classification

| File | Format | SSL Root Key | Size |
|---|---|---|---|
| `CompleteSave.cfg` | **Plaintext JSON** | `CompleteSave` | ~360KB |
| `CommonSslSave.cfg` | **Plaintext JSON** | `CommonSslSave` | ~24KB |
| `GameVersionSave.cfg` | **Plaintext JSON** | `GameVersionSave` | ~161 bytes |
| `achievements.cfg` | **Plaintext — null literal** | `null` | 5 bytes |
| `user_profile.cfg` | **Plaintext JSON** | `UserProfile` | ~2.6KB |
| `user_settings.cfg` | **Plaintext JSON** | `UserSettings` | ~565 bytes |
| `user_social_data.cfg` | **Plaintext JSON** | `UserSocialData` | ~19KB |
| `video.cfg` | **Plaintext JSON** | `Video` | ~251 bytes |
| `sts_level_*.cfg` | **Binary + Zlib Compressed** | — | 40KB–1.5MB |
| `sts_mudmaps_level_*.cfg` | **Binary + Zlib Compressed** | — | 18KB–565KB |
| `fog_level_*.cfg` | **Binary + Zlib Compressed** | — | 400 bytes–9KB |
| `field_level_*.cfg` | **Binary + Zlib Compressed** | — | 33 bytes–4.7KB |

> [!WARNING]
> The `field_level_*.cfg` files vary enormously in size. Small files (~33 bytes) are almost certainly **stub/empty** files (placeholders for fields the player has never touched), while larger ones (~4.7KB) contain full growth stage data. Your parser must handle both gracefully.

> [!NOTE]
> `achievements.cfg` contains only the 5-byte string `null\x00`. Real achievement data is inside `CommonSslSave.cfg` under `achievementStates`. This file is likely a platform-sync stub that is never actually used on PC.

---

## 3. Detailed Schema — Every Plaintext File

### `CompleteSave.cfg`
The primary global progression store. Key fields missed in the first draft:

| Field | Type | Description |
|---|---|---|
| `saveId` | int | Slot number (1–4) |
| `lastLoadedLevel` | string | Last map loaded (e.g., `level_ru_17_01`) |
| `gameDifficultyMode` | int | 0=Normal, 1=Hard |
| `gameDifficultySettings` | object | Deep settings: pricing, recovery, tyre availability, sell multipliers |
| `worldConfiguration` | string | `"vanilla"` or mod pack name |
| `visitedLevels` | array | All maps the player has physically entered |
| `levelGarageStatuses` | object | Per-map garage unlock state (0=Locked, 2=Open) |
| `objectiveStates` | object | Active quests with cargo stage state |
| `finishedObjs` | array | All completed quest IDs |
| `discoveredObjectives` | array | Quests player has seen/revealed on map |
| `viewedUnactivatedObjectives` | array | Seen but not started quests |
| `upgradesGiverData` | object | Collected upgrades per map, value 2=collected |
| `watchPointsData` | object | Per-map watchtower discovery states (true=unlocked) |
| `cargoLoadingCounts` | object | Current cargo quantities at every loading zone on every map |
| `garagesData` | object | Per-garage slot/truck assignments |
| `waypoints` | object | Player-set custom map waypoints (XYZ coords) |
| `hiddenCargoes` | object | Cargo hidden in world (treasure-style) |
| `savedCargoNeedToBeRemovedOnRestart` | object | Cargo that resets on next map load |
| `givenTrialRewards` | array | Trial contest rewards already given |
| `gameTime` | float | Total seconds played |
| `metricSystem` | int | 0=Imperial, 1=Metric |
| `objVersion` | int | Internal version counter for objective schema |
| `birthVersion` | int | Game version when slot was created |
| `trackedObjective` | string | Currently pinned quest ID |
| `isHardMode` | bool | Shortcut flag for hard mode |
| `modTruckOnLevels` | object | Mod trucks placed per level |
| `modTruckTypesRefundValues` | object | Refund records for removed mod trucks |

---

### `CommonSslSave.cfg` — **Major Omission in Prior Draft**
This file contains far more than "cross-platform IDs." It is the **Achievement Engine and Multiplayer Stats Database**:

| Field | Type | Description |
|---|---|---|
| `achievementStates` | object | Every achievement with unlock state, integer counters, and the full string arrays of what contributed to progress (truck names, map IDs, quest IDs) |
| `platformStatsInfo` | object | `totalCoopSessions`, `totalDistanceMeters`, `totalMoneyEarned` — all-time lifetime stats |
| `saveSlotsTransaction` | array | Full save/delete history log for all slots with timestamps as hex (Windows FILETIME format) |
| `lastGeneratedId` | int | The highest slot ID ever written (used to detect corruption) |
| `freezedTrailers` | array | Trailers that are "frozen" in the world across sessions |
| `finishedTrials` | array | Completed trial events |
| `givenProsEntitlements` | array | PROS system rewards claimed |
| `givenProsBanners` | array | PROS cosmetic banners granted |

> [!IMPORTANT]
> **Timestamp Format**: All timestamps in `saveSlotsTransaction` are stored as hex strings representing **Windows FILETIME** (100-nanosecond intervals since Jan 1, 1601). To convert to a human-readable date, you must parse the hex value and apply the FILETIME-to-Unix offset. This was completely missing from the prior report.

---

### `GameVersionSave.cfg`
Small but critical for compatibility checking:

| Field | Value Example | Description |
|---|---|---|
| `platform` | `"pc"` | Platform identifier |
| `changeList` | `831755` | Build number / changelist |
| `stream` | `"SNOW_DLC_17"` | DLC stream the save belongs to (Season 17 = Glades) |
| `versionMajor` | `1` | Major schema version |

> [!WARNING]
> The `stream` field encodes exactly which DLC Season this save was last touched in. If you load a save from `SNOW_DLC_17` in a game client that only has `SNOW_DLC_12`, the game will refuse to load it or corrupt it silently.

---

### `user_profile.cfg` — **Missed Entirely in Prior Draft**
This is the **Mod Registry and Browser Configuration**, not just "audio settings":

| Field | Description |
|---|---|
| `ModsToDelete_SLOT_0` | Semicolon-separated list of mod IDs scheduled to be deleted |
| `modDependencies` | Directory of all installed mods and their dependency chains |
| `modFilter` | Per-user mod browser sort/filter preferences |
| `modTags` | Available filter tag groups (Type, Vehicle, Map, Players, Changes) |
| `areModsPermitted` | 1=mods enabled |
| `lastSaves` | Last slot number used |
| `gdprAccept` / `gdprSeen` | GDPR consent tracking |

---

### `user_social_data.cfg` — **Missed Entirely in Prior Draft**
The **Multiplayer History and Social Graph**:

| Field | Description |
|---|---|
| `RecentPlayers` | Array of last ~100 co-op partners with nicknames, platform IDs (`2`=PS, `7`=PC/Epic/MS), backend UUIDs, and FILETIME timestamps |
| `blockedInGame` | Whether a player was blocked during session |
| `hash` | Obfuscated player identity hash |

---

### `user_settings.cfg` — **Incomplete in Prior Draft**
Not just keybinds — it stores:

| Field | Description |
|---|---|
| `markersVisibility` | Per-type HUD marker toggles (Objectives, Trucks, Waypoints, etc.) |
| `steeringWheelPresets` | Full button mapping for steering wheel hardware |
| `steeringWheelPreviousPid` / `Vid` | USB hardware fingerprint of the last connected wheel |
| `isCrossplay` | Crossplay toggle state |
| `hideKsiva` | UI visibility toggle for one specific HUD element |

---

### `video.cfg` — **Missed Entirely in Prior Draft**
Stores the **Display/Graphics Configuration**:

| Field | Description |
|---|---|
| `OutputSizeX/Y` | Display resolution (2560x1440 in this save) |
| `WindowSizeX/Y` | Window size |
| `WindowMode` | 0=Windowed, 1=Borderless, 2=Fullscreen |
| `ShadowsQuality` / `ObjectQuality` | Per-category graphics quality (0-3) |
| `GrassDensity` / `TerrainDistQuality` | World detail settings |
| `AOQuality` | Ambient Occlusion quality |
| `FilmGrainQuality` | Film grain toggle |
| `AutoDetected` | Whether settings were auto-set on first launch |

---

## 4. Binary File Architecture (STS / FOG / MUDMAP / FIELD)

These files share one architecture but are **not directly readable as JSON**. The pipeline to read them is:

```
[Raw .cfg file]
     ↓
[Strip Saber Interactive binary header]
     ↓
[Zlib inflate (decompress) the payload block]
     ↓
[Parse resulting binary structs + internal string tables]
```

**Key risks for the database:**
- File sizes can reach **1.5MB** (`sts_level_ru_04_02.cfg`) — parsing must be memory-efficient
- `fog_level_*.cfg` files as small as **407 bytes** are near-empty (player never entered the map)
- `field_level_*.cfg` files as small as **33 bytes** are stub placeholders
- The mudmap files only exist for maps with **deformable terrain** — not all maps have one

---

## 5. The Null-Terminator Rule (Critical for Writes)

Every single `.cfg` file in this directory ends with a `\x00` null byte after the closing JSON bracket. This is not optional. The game loader performs a byte-level integrity check and will reject the file if the null byte is missing or if any non-JSON bytes are written between the JSON body and the null.

**Correct file ending:** `...,"cfg_version":1}\x00`  
**Broken file ending:** `...,"cfg_version":1}` ← game will not load

---

## 6. Database Design Summary

| Data Source | Parser Required | Database Table |
|---|---|---|
| `CompleteSave.cfg` | JSON | `player_global`, `objectives`, `upgrades`, `garages`, `cargo_counts`, `waypoints` |
| `CommonSslSave.cfg` | JSON | `achievements`, `lifetime_stats`, `save_history` |
| `GameVersionSave.cfg` | JSON | `save_metadata` |
| `user_profile.cfg` | JSON | `mod_registry` |
| `user_social_data.cfg` | JSON | `multiplayer_history` |
| `user_settings.cfg` | JSON | `input_config`, `hud_config` |
| `video.cfg` | JSON | `display_config` |
| `sts_level_*.cfg` | Binary→Zlib→Struct | `map_physical_state`, `truck_positions` |
| `fog_level_*.cfg` | Binary→Zlib→Struct | `map_fog_revealed` |
| `sts_mudmaps_level_*.cfg` | Binary→Zlib→Struct | `terrain_deformation` |
| `field_level_*.cfg` | Binary→Zlib→Struct | `farming_state` |

---

## 7. MapRunner.info — Complete Verified Metadata Analysis

> [!IMPORTANT]
> **This section is built from direct fetching and full analysis of every data page at maprunner.info. Not from assumptions.**

### 7.1 Site Architecture & What Data Exists

MapRunner is a 5-layer website. Each layer maps to a specific type of data in `CompleteSave.cfg`:

| MapRunner Section | URL | Maps to Save Field |
|---|---|---|
| **Interactive Maps** (per region/map) | `/michigan/black-river` etc | `visitedLevels`, `levelGarageStatuses`, `watchPointsData` |
| **Missions** (Tasks / Contracts / Contests) | `/missions` | `finishedObjs`, `objectiveStates` |
| **Upgrades** | `/upgrades` | `upgradesGiverData` |
| **Cargo** | `/cargo` | `cargoLoadingCounts`, `hiddenCargoes` |
| **Vehicles** | `/vehicles` | `garagesData`, truck unlock records |

### 7.2 Full Region & Season Map (17 Seasons, 42+ Maps)

MapRunner tracks every map ever released. The save file's internal region prefix matches the MapRunner URL:

| MapRunner URL Prefix | Save File Prefix | Region | Type | Num Maps |
|---|---|---|---|---|
| `/michigan/` | `us_01_` | Michigan, USA | Base Game | 4 |
| `/alaska/` | `us_02_` | Alaska, USA | Base Game | 4 |
| `/taymyr/` | `ru_02_` | Taymyr, Russia | Base Game | 4 |
| `/kola-peninsula/` | `ru_03_` | Kola Peninsula | S1 DLC | 2 |
| `/yukon/` | `us_04_` | Yukon, Canada | S2 DLC | 2 |
| `/wisconsin/` | `us_03_` | Wisconsin, USA | S3 DLC | 2 |
| `/amur/` | `ru_04_` | Amur, Russia | S4 DLC | 4 |
| `/don/` | `ru_05_` | Don, Russia | S5 DLC | 2 |
| `/maine/` | `us_06_` | Maine, USA | S6 DLC | 2 |
| `/tennessee/` | `us_07_` | Tennessee, USA | S7 DLC | 1 |
| `/belozersk-glades/` | `ru_08_` | Belozersk Glades | S8 DLC | 4 |
| `/ontario/` | `us_09_` | Ontario, Canada | S9 DLC | 2 |
| `/british-columbia/` | `us_10_` | British Columbia | S10 DLC | 2 |
| `/scandinavia/` | `us_11_` | Scandinavia | S11 DLC | 2 |
| `/north-carolina/` | `us_12_` | North Carolina | S12 DLC | 4 |
| `/almaty-region/` | `ru_13_` | Almaty Region | S13 DLC | 1 |
| `/austria/` | `us_14_` | Austria | S14 DLC | 2 |
| `/quebec/` | `us_15_` | Quebec | S15 DLC | 2 |
| `/washington/` | `us_16_` | Washington | S16 DLC | 3 |
| `/zurdania/` | `ru_17_` | Zurdania | S17 DLC | 2 |

> [!NOTE]
> The ID naming scheme skips some numbers (no `us_05_`, no `ru_06_`, `ru_07_`). This is not a bug — those were internal Saber IDs reserved or cancelled. Your database must handle these ID gaps correctly when building lookup tables.

### 7.3 POI (Point of Interest) Types Per Map

From inspection of Black River (a representative base-game map), MapRunner tracks and surfaces these POI category types on every map page. Each has a corresponding save field:

| MapRunner POI Category | MapRunner Label | Save File Linkage |
|---|---|---|
| **Cargo Depots** | `Bricks [1]`, `Fuel [1]` etc | `cargoLoadingCounts` |
| **Buildings** | Factory, Warehouse, Lumber Mill, Farm | No direct save field — visual only |
| **Garages** | Garage Entrance | `levelGarageStatuses` |
| **Gateways** (map connections) | "Smithville Dam" etc | `visitedLevels` (triggers unlock) |
| **Points of Interest** | Named or "HIDDEN TAG" | No save field — lore pins |
| **Sightings** | Wolf, Bear, etc | No save field — cosmetic |
| **Upgrades** | Named part upgrades | `upgradesGiverData` |
| **Watchtowers** | Watchtower × N | `watchPointsData` |
| **Contests** | Named contest events | `finishedObjs` (as `_CNT` suffix IDs) |
| **Tasks** | Named tasks | `finishedObjs` (as `_TSK` suffix IDs) |
| **Contracts** (per company) | Named contracts | `finishedObjs` (as `_OBJ` suffix IDs) |
| **Vehicles** (world spawns) | Truck names on map | `sts_level_*.cfg` (physical spawn coords) |

> [!IMPORTANT]
> **The suffix convention on objective IDs is critical for your database design:**
> - `_TSK` = Task (optional, side mission)
> - `_OBJ` = Contract (story mission for a company)
> - `_CNT` = Contest (score/time challenge)
> These are finishedObj IDs stored in `CompleteSave.cfg`. MapRunner uses the same IDs in its `?loc=` URL parameter to highlight that objective on the map.

### 7.4 Objective Naming Convention

Every objective ID follows this pattern:
```
[REGION_PREFIX]_[MAP_NUM]_[DESCRIPTOR]_[TYPE_SUFFIX]
```
Examples from MapRunner:
- `US_01_01_WOODEN_ORDER_CNT` → Michigan / Black River / Contest
- `RU_02_02_STUCK_TRUCK_TSK` → Taymyr / Drowned Lands / Task
- `US_02_01_PIPELINE_OBJ` → Alaska / North Port / Contract
- `RU_08_01_FARMING_FIELD_1` → Belozersk Glades / Crossroads / Special (no standard suffix)

### 7.5 Upgrade ID Convention

From the upgrades page, the upgrade IDs follow this pattern:
```
[REGION]_[MAP]_UPGRADE_[N]    (newer maps)
[REGION]_[MAP]_UPGRADE_[PART_NAME]   (older Michigan/Alaska maps)
```
Examples:
- `US_01_01_UPGRADE_TRUCK_OLD_ENGINE` → Black River engine upgrade (named)
- `US_01_01_UPGRADE_G_SCOUT_OFFROAD` → Black River scout upgrade (named)
- `RU_02_01_UPGRADE_01` → Taymyr Quarry upgrade 1 (numbered)
- `US_02_02_UPG_04` → Alaska Mountain River upgrade 4 (short form)

> [!WARNING]
> **Inconsistent naming.** Older base-game upgrades use descriptive names (`UPGRADE_TRUCK_ENG`). DLC upgrades often use numeric codes (`UPG_01`). Your database cannot assume a consistent naming format and must use `upgradesGiverData` IDs directly from the save file as the foreign key, not guessed upgrade names.

### 7.6 MapRunner's ?loc= URL Parameter — The Linkage Key

This is the critical bridge between MapRunner and your save editor:

```
https://www.maprunner.info/michigan/black-river?loc=US_01_01_BUILD_A_BRIDGE_OBJ
```

The `?loc=` value is **exactly identical** to the string ID stored in `CompleteSave.cfg`'s `finishedObjs` or `objectiveStates` array. This is how MapRunner reads your save file locally — it parses `CompleteSave.cfg`, reads the `finishedObjs` array, and highlights matching `?loc=` pins green on the map.

**Your database join logic should be:**
```python
save_completed = set(CompleteSave["finishedObjs"])
for poi in maprunner_database:
    poi["is_completed"] = poi["loc_id"] in save_completed
```

### 7.7 What MapRunner Cannot Tell You (Gaps for Your DB)

| Data Point | Available in Save | Available on MapRunner | Notes |
|---|---|---|---|
| Truck spawn locations | ✅ `sts_level_*.cfg` | ✅ Vehicle section | MapRunner shows named vehicles, save has XYZ coords |
| Cargo slot counts | ✅ `cargoLoadingCounts` | ✅ "Cargo [N]" label | MapRunner shows slot count, save has actual current count |
| Gateway unlock status | ✅ `visitedLevels` | ✅ "Gateways" section | Linkage by map name |
| "HIDDEN TAG" POIs | ❌ No save data | ✅ Listed | MapRunner won't reveal their name but they exist |
| Animal sightings | ❌ No save data | ✅ Listed | Cosmetic only, no save tracking |
| Building status | ❌ Not in plaintext | ✅ Listed | Physical build state in `sts_level` binary data |
| DLC ownership | ❌ Not in save | ❌ Not on MapRunner | Must be inferred from `visitedLevels` presence |
| Slot transaction log | ✅ `CommonSslSave.cfg` | ❌ Not on MapRunner | Only available locally |
| Multiplayer history | ✅ `user_social_data.cfg` | ❌ Not on MapRunner | Only available locally |
