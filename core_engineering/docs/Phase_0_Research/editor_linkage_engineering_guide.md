# SnowRunner Save Editor — Linkage Engineering Guide

> [!IMPORTANT]
> This document describes **how to correctly connect every data source** when building a SnowRunner editor.
> It is the "how to build it" companion to the `save_architecture_db_schema.md` "what exists" document.

---

## Part 1: The Three Data Sources You Must Bridge

```
┌─────────────────────────────────────────────────────────────────────┐
│                     SNOWRUNNER EDITOR DATA PLANE                    │
│                                                                     │
│  ┌─────────────────┐   ┌──────────────────┐   ┌─────────────────┐  │
│  │ SOURCE A         │   │ SOURCE B          │   │ SOURCE C        │  │
│  │ CompleteSave.cfg │   │ Binary .cfg Files │   │ MapRunner       │  │
│  │ (Plaintext JSON) │   │ STS / FOG / FIELD │   │ Static Metadata │  │
│  │                 │   │ (Zlib Compressed) │   │ (Bundled JSON)  │  │
│  └────────┬────────┘   └────────┬──────────┘   └────────┬────────┘  │
│           │                    │                        │           │
│           └────────────────────┴────────────────────────┤           │
│                                                         ▼           │
│                         ┌─────────────────────┐                     │
│                         │  EDITOR RUNTIME DB  │                     │
│                         │   (In-Memory Only)  │                     │
│                         │  READ-ONLY by deflt │                     │
│                         └─────────────────────┘                     │
└─────────────────────────────────────────────────────────────────────┘
```

**Source A** — What the player has done (mutable, the file you edit)  
**Source B** — Where things are physically in the world (readable but never edited directly)  
**Source C** — The human-readable translation layer (static, bundled with your editor)

---

## Part 2: Source C — Building Your Static MapRunner Registry

Before you can do anything, you need a static translation table bundled into your editor. This is your internal equivalent of what MapRunner.info shows visually.

### Step 1: Define the Registry Schema

Create a file: `core_engineering/data/maprunner_registry.json`

```json
{
  "maps": {
    "level_us_01_01": {
      "human_name": "Black River",
      "region": "Michigan, USA",
      "season": "Base Game",
      "maprunner_url": "/michigan/black-river",
      "internal_prefix": "US_01_01",
      "save_file_slug": "sts_level_us_01_01",
      "has_farming": false,
      "has_mudmaps": true
    },
    "level_ru_08_01": {
      "human_name": "Crossroads",
      "region": "Belozersk Glades",
      "season": "Season 8: Grand Harvest",
      "maprunner_url": "/belozersk-glades/crossroads",
      "internal_prefix": "RU_08_01",
      "save_file_slug": "sts_level_ru_08_01",
      "has_farming": true,
      "has_mudmaps": true
    }
  },

  "objectives": {
    "US_01_01_BUILD_A_BRIDGE_OBJ": {
      "type": "contract",
      "human_name": "Old Bridge Reconstruction",
      "map_id": "level_us_01_01",
      "company": "STEEL RIVER TOWNSHIP",
      "xp_reward": 1400,
      "money_reward": 3500
    },
    "US_01_01_WOODEN_BRIDGE_TSK": {
      "type": "task",
      "human_name": "Wooden Bridge",
      "map_id": "level_us_01_01",
      "company": null,
      "xp_reward": 350,
      "money_reward": 750
    },
    "US_01_01_WOODEN_ORDER_CNT": {
      "type": "contest",
      "human_name": "Pinewood Express",
      "map_id": "level_us_01_01",
      "company": null,
      "xp_reward": 0,
      "money_reward": 1200
    }
  },

  "upgrades": {
    "US_01_01_UPGRADE_TRUCK_OLD_ENGINE": {
      "human_name": "Si-6V/2100T Engine",
      "upgrade_type": "engine",
      "compatible_trucks": ["international_fleetstar_f2070a"],
      "map_id": "level_us_01_01"
    },
    "US_01_01_UPGRADE_G_SCOUT_OFFROAD": {
      "human_name": "Off-Road Suspension",
      "upgrade_type": "suspension",
      "compatible_trucks": ["all_scouts"],
      "map_id": "level_us_01_01"
    }
  },

  "watchtowers": {
    "level_us_01_01_US_01_01_W1": {
      "human_name": "Black River Watchtower 1",
      "map_id": "level_us_01_01"
    }
  }
}
```

> [!NOTE]
> You do not need to scrape MapRunner to build this. The IDs and names can be sourced from MapRunner's URL params (`?loc=`) and confirmed against `CommonSslSave.cfg` achievement arrays, which contain the complete set of valid IDs for quests, upgrades, and watchtowers as verified string lists.

---

## Part 3: Source A Loading Pipeline — CompleteSave.cfg

### Step 2: The Ingestion Pattern

```python
# core_engineering/engine/save_loader.py

import json
import pathlib

class SaveLoader:
    """
    Loads and validates all plaintext .cfg files from a save slot directory.
    Stores data in-memory. Never modifies files unless explicitly instructed.
    """

    PLAINTEXT_FILES = [
        "CompleteSave.cfg",
        "CommonSslSave.cfg",
        "GameVersionSave.cfg",
        "achievements.cfg",
        "user_profile.cfg",
        "user_settings.cfg",
        "user_social_data.cfg",
        "video.cfg",
    ]

    def __init__(self, save_dir: pathlib.Path):
        self.save_dir = save_dir
        self.data = {}
        self._null_byte_positions = {}  # Track where \x00 is in each file

    def load_all(self):
        for filename in self.PLAINTEXT_FILES:
            filepath = self.save_dir / filename
            if not filepath.exists():
                continue
            self._load_plaintext(filepath)

    def _load_plaintext(self, filepath: pathlib.Path):
        # CRITICAL: Read as bytes first to detect and preserve the null terminator
        raw_bytes = filepath.read_bytes()

        # Confirm null terminator presence
        if raw_bytes[-1] != 0x00:
            raise ValueError(f"INTEGRITY FAIL: {filepath.name} is missing null terminator. "
                             f"File may be corrupt or externally modified.")

        # Record the null byte position for safe writing later
        self._null_byte_positions[filepath.name] = len(raw_bytes) - 1

        # Decode JSON body (strip the null byte)
        json_body = raw_bytes[:-1].decode("utf-8")

        # Handle the special case: achievements.cfg is literally "null"
        if json_body.strip() == "null":
            self.data[filepath.name] = None
            return

        parsed = json.loads(json_body)
        self.data[filepath.name] = parsed

    def get_complete_save(self) -> dict:
        return self.data.get("CompleteSave.cfg", {}).get("CompleteSave", {}).get("SslValue", {})

    def get_common_ssl(self) -> dict:
        return self.data.get("CommonSslSave.cfg", {}).get("CommonSslSave", {}).get("SslValue", {})

    def get_game_version(self) -> dict:
        return self.data.get("GameVersionSave.cfg", {}).get("GameVersionSave", {}).get("SslValue", {})
```

### Step 3: The Safe Write Pattern

```python
    def write_plaintext_safe(self, filepath: pathlib.Path, mutated_data: dict):
        """
        Write back to a .cfg file. ALWAYS:
        1. Adds the null byte terminator
        2. Uses compact JSON (no extra spaces = smaller file, matches game format)
        3. Validates the data can round-trip before writing
        """
        # Compact JSON with no trailing spaces (matches Saber's format)
        json_body = json.dumps(mutated_data, separators=(",", ":"), ensure_ascii=False)

        # Re-encode with null terminator
        output_bytes = json_body.encode("utf-8") + b"\x00"

        # Validate round-trip before committing to disk
        verify = json.loads(output_bytes[:-1].decode("utf-8"))
        if verify != mutated_data:
            raise RuntimeError("WRITE ABORTED: Round-trip validation failed. Data corruption risk.")

        filepath.write_bytes(output_bytes)
```

---

## Part 4: Establishing the Linkages — The Join Engine

This is the heart of the editor. Once Source A and Source C are loaded, you join them.

### Step 4: The Objective Linkage

```python
# core_engineering/engine/linkage_engine.py

class LinkageEngine:

    def __init__(self, save_loader: SaveLoader, registry: dict):
        self.save = save_loader.get_complete_save()
        self.registry = registry

    def build_objective_status_table(self) -> list[dict]:
        """
        Joins CompleteSave.cfg objective data with MapRunner registry.
        Returns a list of every known objective with its live save state.
        """
        # Pull the three relevant arrays from the save
        finished  = set(self.save.get("finishedObjs", []))
        active    = {k: v for k, v in self.save.get("objectiveStates", {}).items()}
        discovered = set(self.save.get("discoveredObjectives", []))

        result = []
        for obj_id, meta in self.registry["objectives"].items():
            # Determine state by checking which array the ID appears in
            if obj_id in finished:
                state = "COMPLETED"
            elif obj_id in active:
                state = "ACTIVE"
                state_detail = active[obj_id]   # Contains cargo counts, stage info
            elif obj_id in discovered:
                state = "DISCOVERED"
            else:
                state = "UNDISCOVERED"

            result.append({
                "id": obj_id,
                "human_name": meta.get("human_name", obj_id),
                "type": meta.get("type"),          # task / contract / contest
                "map_id": meta.get("map_id"),
                "region": self.registry["maps"].get(meta.get("map_id"), {}).get("region"),
                "company": meta.get("company"),
                "state": state,
                "xp_reward": meta.get("xp_reward", 0),
                "money_reward": meta.get("money_reward", 0)
            })

        return result
```

### Step 5: The Upgrade Linkage

```python
    def build_upgrade_status_table(self) -> list[dict]:
        """
        Joins CompleteSave.cfg upgradesGiverData with MapRunner registry.
        Returns every known upgrade with its collected/not-collected state.
        """
        # upgradesGiverData is a nested dict: {level_id: {upgrade_id: int_value}}
        # Value of 2 = collected, 0 or missing = not collected
        upgrades_data = self.save.get("upgradesGiverData", {})

        # Flatten to a lookup: upgrade_id -> collected bool
        collected = {}
        for level_id, upgrades in upgrades_data.items():
            for upgrade_id, value in upgrades.items():
                collected[upgrade_id] = (value == 2)

        result = []
        for upg_id, meta in self.registry["upgrades"].items():
            result.append({
                "id": upg_id,
                "human_name": meta.get("human_name", upg_id),
                "upgrade_type": meta.get("upgrade_type"),
                "map_id": meta.get("map_id"),
                "region": self.registry["maps"].get(meta.get("map_id"), {}).get("region"),
                "is_collected": collected.get(upg_id, False)
            })

        return result
```

### Step 6: The Watchtower Linkage

```python
    def build_watchtower_status_table(self) -> list[dict]:
        """
        Joins watchPointsData with the watchtower registry.
        Also cross-references CommonSslSave achievement 'WatchPoints_ExploreAll'
        for a secondary confirmation.
        """
        # watchPointsData: {level_id: {tower_id: true/false}}
        watch_data = self.save.get("watchPointsData", {})

        # Flatten: combine level_id + tower_id for the full compound key
        # The key format in achievementStates is: "level_us_01_01_US_01_01_W1"
        discovered_compound = set()
        for level_id, towers in watch_data.items():
            for tower_id, is_found in towers.items():
                if is_found:
                    discovered_compound.add(f"{level_id}_{tower_id}")

        result = []
        for tower_compound_id, meta in self.registry["watchtowers"].items():
            result.append({
                "id": tower_compound_id,
                "human_name": meta.get("human_name", tower_compound_id),
                "map_id": meta.get("map_id"),
                "is_discovered": tower_compound_id in discovered_compound
            })

        return result
```

### Step 7: The Map/Garage Linkage

```python
    def build_map_status_table(self) -> list[dict]:
        """
        Joins levelGarageStatuses and visitedLevels with map metadata.
        """
        garage_statuses = self.save.get("levelGarageStatuses", {})
        visited = set(self.save.get("visitedLevels", []))

        result = []
        for level_id, meta in self.registry["maps"].items():
            # Garage status: 0=Locked, 2=Unlocked. May not exist if never visited.
            garage_state_val = garage_statuses.get(level_id, 0)

            result.append({
                "level_id": level_id,
                "human_name": meta.get("human_name"),
                "region": meta.get("region"),
                "season": meta.get("season"),
                "is_visited": level_id in visited,
                "garage_unlocked": garage_state_val == 2,
            })

        return result
```

---

## Part 5: Source B — Binary File Linkages (STS / FOG)

These are read-only for safety. Only parse them if you need spatial data.

### Step 8: Binary File Decoder

```python
# core_engineering/engine/binary_decoder.py
import zlib
import struct

class BinaryDecoder:
    """
    Handles Saber Interactive's proprietary binary+zlib format
    for STS, FOG, MUDMAP, and FIELD level files.
    """

    # Saber's binary header is typically 8-20 bytes before the zlib stream.
    # The zlib magic bytes are always 0x78 0x9C (default compression)
    ZLIB_MAGIC = b"\x78\x9c"

    def decompress(self, filepath) -> bytes:
        raw = pathlib.Path(filepath).read_bytes()

        # Find the zlib payload start by scanning for magic bytes
        zlib_start = raw.find(self.ZLIB_MAGIC)
        if zlib_start == -1:
            raise ValueError(f"No zlib magic bytes found in {filepath}. "
                             f"File may use a different compression scheme.")

        # Decompress the payload
        compressed_payload = raw[zlib_start:]
        try:
            decompressed = zlib.decompress(compressed_payload)
        except zlib.error as e:
            raise ValueError(f"Zlib decompression failed for {filepath}: {e}")

        return decompressed

    def get_fog_data(self, level_id: str, save_dir: pathlib.Path) -> dict | None:
        """
        Returns fog revealed state for a given level as a structured dict.
        Returns None if the file is a stub (too small to contain real data).
        """
        fog_file = save_dir / f"fog_level_{level_id}.cfg"
        if not fog_file.exists():
            return None

        # Stubs are typically < 100 bytes
        if fog_file.stat().st_size < 100:
            return {"is_stub": True, "revealed_zones": []}

        raw_decompressed = self.decompress(fog_file)

        # The decompressed data contains coordinate arrays representing revealed areas.
        # Parsing requires iterating in fixed-size struct chunks.
        # Format: series of (x: float32, y: float32) coordinate pairs
        zones = []
        chunk_size = 8  # 4 bytes x + 4 bytes y
        for i in range(0, len(raw_decompressed) - chunk_size + 1, chunk_size):
            chunk = raw_decompressed[i:i + chunk_size]
            try:
                x, y = struct.unpack("<ff", chunk)
                # Filter out obviously invalid coordinates (NaN, Inf, extreme values)
                if abs(x) < 100000 and abs(y) < 100000:
                    zones.append({"x": round(x, 2), "y": round(y, 2)})
            except struct.error:
                break

        return {"is_stub": False, "revealed_zones": zones}
```

### Step 9: Linking Fog State to Map Registry

```python
    def build_fog_status_table(
        self,
        binary_decoder: BinaryDecoder,
        save_dir: pathlib.Path
    ) -> list[dict]:
        """
        Joins fog_level_*.cfg decompressed data with map registry.
        Produces a table of fog reveal status per map.
        """
        result = []
        for level_id, meta in self.registry["maps"].items():
            fog_data = binary_decoder.get_fog_data(level_id, save_dir)

            if fog_data is None:
                reveal_status = "FILE_MISSING"
                zone_count = 0
            elif fog_data.get("is_stub"):
                reveal_status = "NEVER_VISITED"
                zone_count = 0
            else:
                zone_count = len(fog_data["revealed_zones"])
                reveal_status = "PARTIAL" if zone_count < 500 else "FULL"

            result.append({
                "level_id": level_id,
                "human_name": meta.get("human_name"),
                "fog_status": reveal_status,
                "revealed_zone_count": zone_count
            })

        return result
```

---

## Part 6: The Editor's Mutation Safety Rules

> [!CAUTION]
> **Breaking these rules will corrupt the player's save.** Every mutation must pass all safety checks before writing.

### Rule 1: Always Backup First

```python
import shutil
import datetime

def create_backup(save_dir: pathlib.Path) -> pathlib.Path:
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_dir = save_dir.parent / f"backup_{timestamp}"
    shutil.copytree(save_dir, backup_dir)
    return backup_dir
```

### Rule 2: DLC-Gated Mutations

Before setting a quest to completed or unlocking a map, verify the player's DLC:
```python
def is_dlc_owned(level_id: str, save: dict) -> bool:
    """
    Infer DLC ownership from visitedLevels.
    If the player has never visited a DLC map, assume they don't own the DLC.
    Writing DLC objective IDs into finishedObjs for unowned DLC causes no visible
    effect but wastes array space and can confuse the objective resolver.
    """
    visited = set(save.get("visitedLevels", []))
    # Get all maps in the same season group
    # If any sibling map has been visited, DLC is owned
    season_prefix = level_id[:len("level_us_01")]  # e.g., "level_us_04"
    return any(v.startswith(season_prefix) for v in visited)
```

### Rule 3: Pair CompleteSave + STS for Structural Objectives

When completing an objective that **physically alters the world** (bridge, building), you cannot only write to `CompleteSave.cfg`. The `sts_level_*.cfg` binary file must also be updated.

```python
# This is the single most dangerous operation in the editor
STRUCTURAL_OBJECTIVE_TYPES = {
    # Objectives that change a physical object's state in the world
    # These require a paired STS mutation or the world will desync
    "US_01_01_BUILD_A_BRIDGE_OBJ": {"sts_object": "BRIDGE_US_01_01_A", "sts_state": 2},
    "US_02_01_PIPELINE_OBJ":       {"sts_object": "PIPELINE_US_02_01", "sts_state": 3},
    # Add all bridge/building objectives here
}

def is_structural(obj_id: str) -> bool:
    return obj_id in STRUCTURAL_OBJECTIVE_TYPES

def complete_objective_safe(obj_id: str, save: dict) -> dict:
    """
    Adds an objective to finishedObjs safely.
    Warns if the objective is structural (requires binary STS update).
    """
    if is_structural(obj_id):
        raise NotImplementedError(
            f"'{obj_id}' is a structural objective. Completing it requires "
            f"a paired binary STS file mutation, which has not been implemented. "
            f"Completing only via CompleteSave will cause world desync."
        )

    # Non-structural objectives are safe to complete via JSON alone
    finished = list(save.get("finishedObjs", []))
    if obj_id not in finished:
        finished.append(obj_id)

    # Also remove from active objectiveStates if present
    obj_states = dict(save.get("objectiveStates", {}))
    obj_states.pop(obj_id, None)

    save["finishedObjs"] = finished
    save["objectiveStates"] = obj_states
    return save
```

### Rule 4: Upgrade Collection Must Match Giver Map

```python
def collect_upgrade_safe(upgrade_id: str, save: dict, registry: dict) -> dict:
    """
    Sets an upgrade to collected in upgradesGiverData.
    Must use the correct level_id as the outer key, not a generic key.
    """
    upg_meta = registry["upgrades"].get(upgrade_id)
    if not upg_meta:
        raise KeyError(f"Unknown upgrade ID: {upgrade_id}")

    level_id = upg_meta["map_id"]  # e.g., "level_us_01_01"

    upgrades_giver = dict(save.get("upgradesGiverData", {}))
    if level_id not in upgrades_giver:
        upgrades_giver[level_id] = {}

    upgrades_giver[level_id][upgrade_id] = 2  # 2 = collected
    save["upgradesGiverData"] = upgrades_giver
    return save
```

### Rule 5: Watchtower Unlock Requires Both Arrays

Unlocking a watchtower must touch **two** places in the save file:
1. `watchPointsData` in `CompleteSave.cfg`
2. `WatchPoints_ExploreAll.valuesArray` in `CommonSslSave.cfg`

```python
def unlock_watchtower_safe(
    tower_compound_id: str,   # e.g., "level_us_01_01_US_01_01_W1"
    complete_save: dict,
    common_ssl: dict,
    registry: dict
) -> tuple[dict, dict]:
    """
    Unlocks a watchtower. MUST update both CompleteSave and CommonSslSave.
    Returns mutated (complete_save, common_ssl) tuple.
    """
    tower_meta = registry["watchtowers"].get(tower_compound_id)
    if not tower_meta:
        raise KeyError(f"Unknown watchtower compound ID: {tower_compound_id}")

    level_id = tower_meta["map_id"]  # e.g., "level_us_01_01"
    # The tower sub-ID is the part after the level_id prefix
    tower_sub_id = tower_compound_id[len(level_id) + 1:]  # e.g., "US_01_01_W1"

    # 1. Update CompleteSave.cfg watchPointsData
    watch_points = dict(complete_save.get("watchPointsData", {}))
    if level_id not in watch_points:
        watch_points[level_id] = {}
    watch_points[level_id][tower_sub_id] = True
    complete_save["watchPointsData"] = watch_points

    # 2. Update CommonSslSave.cfg achievement array
    ach = common_ssl.get("achievementStates", {})
    wp_achievement = ach.get("WatchPoints_ExploreAll", {})
    values_array = list(wp_achievement.get("valuesArray", []))

    if tower_compound_id not in values_array:
        values_array.append(tower_compound_id)
        wp_achievement["valuesArray"] = values_array
        wp_achievement["currentValue"] = len(values_array)
        ach["WatchPoints_ExploreAll"] = wp_achievement
        common_ssl["achievementStates"] = ach

    return complete_save, common_ssl
```

---

## Part 7: The Editor's Runtime Data Model

Tie everything together in one central class:

```python
# core_engineering/engine/editor_context.py

class EditorContext:
    """
    The single source of truth for the editor at runtime.
    Loads all data, builds all linkage tables, and exposes safe mutation methods.
    """

    def __init__(self, save_dir: pathlib.Path, registry_path: pathlib.Path):
        self.save_dir = save_dir
        self.registry = json.loads(registry_path.read_text(encoding="utf-8"))

        # Step 1: Load all plaintext files
        self.loader = SaveLoader(save_dir)
        self.loader.load_all()

        # Step 2: Extract save state
        self._complete_save = self.loader.get_complete_save()
        self._common_ssl    = self.loader.get_common_ssl()
        self._game_version  = self.loader.get_game_version()

        # Validate DLC stream compatibility
        stream = self._game_version.get("stream", "UNKNOWN")
        self.dlc_season = int(stream.replace("SNOW_DLC_", "")) if "SNOW_DLC_" in stream else 0

        # Step 3: Build all linkage tables (read-only joins)
        self.engine = LinkageEngine(self.loader, self.registry)
        self.binary = BinaryDecoder()

        self.objectives  = self.engine.build_objective_status_table()
        self.upgrades    = self.engine.build_upgrade_status_table()
        self.watchtowers = self.engine.build_watchtower_status_table()
        self.maps        = self.engine.build_map_status_table()
        self.fog_states  = self.engine.build_fog_status_table(self.binary, save_dir)

    # ── Query Methods (Read-Only) ──────────────────────────────────────
    def get_objectives_by_map(self, level_id: str) -> list[dict]:
        return [o for o in self.objectives if o["map_id"] == level_id]

    def get_uncollected_upgrades(self) -> list[dict]:
        return [u for u in self.upgrades if not u["is_collected"]]

    def get_completion_stats(self) -> dict:
        total_obj  = len(self.objectives)
        done_obj   = sum(1 for o in self.objectives if o["state"] == "COMPLETED")
        total_upg  = len(self.upgrades)
        done_upg   = sum(1 for u in self.upgrades if u["is_collected"])
        total_wt   = len(self.watchtowers)
        done_wt    = sum(1 for w in self.watchtowers if w["is_discovered"])

        return {
            "objectives":  {"completed": done_obj,  "total": total_obj},
            "upgrades":    {"collected": done_upg,  "total": total_upg},
            "watchtowers": {"discovered": done_wt, "total": total_wt},
            "completion_pct": round((done_obj + done_upg + done_wt) /
                                    max(total_obj + total_upg + total_wt, 1) * 100, 1)
        }

    # ── Mutation Methods (Write) ───────────────────────────────────────
    def complete_objective(self, obj_id: str):
        backup = create_backup(self.save_dir)
        try:
            self._complete_save = complete_objective_safe(obj_id, self._complete_save)
            self._flush_complete_save()
        except Exception as e:
            # Restore backup on any failure
            shutil.rmtree(self.save_dir)
            shutil.copytree(backup, self.save_dir)
            raise RuntimeError(f"Mutation failed, backup restored: {e}") from e

    def _flush_complete_save(self):
        filepath = self.save_dir / "CompleteSave.cfg"
        full_structure = self.loader.data["CompleteSave.cfg"]
        full_structure["CompleteSave"]["SslValue"] = self._complete_save
        self.loader.write_plaintext_safe(filepath, full_structure)
```

---

## Part 8: Feature-to-Linkage Reference Card

Use this as your implementation checklist when building each editor tab:

| Editor Feature | Files Read | Fields Used | Files Written | Safety Rule |
|---|---|---|---|---|
| **Show map progress** | `CompleteSave.cfg` | `visitedLevels`, `levelGarageStatuses` | — | Read-only |
| **Complete a task** | `CompleteSave.cfg` | `finishedObjs`, `objectiveStates` | `CompleteSave.cfg` | Not structural only |
| **Collect an upgrade** | `CompleteSave.cfg` | `upgradesGiverData` | `CompleteSave.cfg` | Use correct `level_id` key |
| **Unlock a watchtower** | `CompleteSave.cfg` + `CommonSslSave.cfg` | `watchPointsData` + `WatchPoints_ExploreAll` | Both files | Must update BOTH |
| **Reveal fog on a map** | `fog_level_*.cfg` | Zlib binary zones | `fog_level_*.cfg` | Binary write, VERY risky |
| **Unlock a garage** | `CompleteSave.cfg` | `levelGarageStatuses` | `CompleteSave.cfg` | Set value to `2` |
| **Show lifetime stats** | `CommonSslSave.cfg` | `platformStatsInfo` | — | Read-only |
| **Show co-op history** | `user_social_data.cfg` | `RecentPlayers` | — | Read-only |
| **Add money/XP** | `CompleteSave.cfg` | `money`, `experience` | `CompleteSave.cfg` | Cap values to valid int range |
| **Check DLC ownership** | `CompleteSave.cfg` | `visitedLevels` | — | Infer, never assume |
| **Bridge/building construction** | `CompleteSave.cfg` + `sts_level_*.cfg` | `finishedObjs` + binary struct | Both | **NOT SAFE without STS binary writer** |
