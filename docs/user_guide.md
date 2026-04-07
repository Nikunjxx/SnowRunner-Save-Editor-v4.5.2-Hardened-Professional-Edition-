# 🧭 User Guide — SnowRunner Save Editor (v110.40)

Welcome to the definitive guide for managing your SnowRunner progress with the **NextGen Save Editor**. This tool is built for safety and precision.

---

## 1. Finding Your Save Folder

SnowRunner stores save data in different locations depending on your platform:

### 🎮 Steam
`C:\Program Files (x86)\Steam\userdata\<your-steam-id>\1234560\remote`
*(Note: 1234560 is the Steam App ID for SnowRunner)*

### 🎮 Epic Games / Microsoft Store (Common)
`%USERPROFILE%\Documents\My Games\SnowRunner\base\storage\<user-id>`

---

## 2. Understanding the Slot System

SnowRunner supports up to **4 save slots**. Each slot uses a specific file naming convention:

*   **Slot 1**: `CompleteSave.cfg` (No prefix)
*   **Slot 2**: `1_CompleteSave.cfg`
*   **Slot 3**: `2_CompleteSave.cfg`
*   **Slot 4**: `3_CompleteSave.cfg`

**The Editor automatically detects which slot you are viewing.** You don't need to rename files manually.

---

## 3. Tab-by-Tab Instructions

### 🛡️ Sanitizer (Health Check)
**Use this first!** The Sanitizer scans for structural corruption and legacy "bad edits" from other tools.
- **Action**: Click "Validate Current Save".
- **Benefit**: Fixes broken garage linkages and orphaned truck data.

### 🗺️ Regions (Map Management)
Control the visibility and accessibility of game maps.
- **Unlock Maps**: Makes all maps in a region selectable.
- **Unlock Garages**: Teleports and activates garages.
- **Reveal Watchtowers**: Removes fog and grants the "Watchtower Discovered" status.

### 🛠️ Upgrades (Discovery)
Batch-discover all vehicle upgrades in the world.
- **Filter**: Use the sidebar to select a specific map.
- **Discover All**: Adds all upgrades to your inventory.
- **STS Sync (Premium Feature)**: Removes the yellow upgrade pick-up markers from the physical game world.

### 🚚 Vehicles (Fleet Management)
Manage your owned trucks and trailers.
- **Repair/Refuel**: Instantly restores truck health and fuel.
- **Garage Move**: Safely teleports a truck to its home garage.
- **Coordinate Move**: (Advanced) Manually set X/Y/Z positions.

### 🎯 Objectives+ (Missions & Rewards)
The most advanced mission completion system available.
- **Complete Selected**: Finishes missions and applies **Money + XP rewards** automatically.
- **Reset Mission**: Reverts a mission to its starting state.
- **Safe Mode**: Enforces a Level 30 XP cap to prevent save-profile corruption (128,500 XP maximum).

### 📦 Scenarios (Automation)
Presets that bundle multiple complex actions into a single atomic change.
- **Explorer Mode**: Unlocks all maps, garages, and reveals all watchtowers in the current region.
- **Logistics Master**: Repairs and refuels every truck currently in the world.

---

## 🛡️ The Backup & Rollback System

The NextGen Editor generates an **automatic backup** every time you click "Apply Changes".

*   **Backups Folder**: Located in the same directory as the editor EXE.
*   **Automatic Restore**: If the tool detects that a change failed validation, it will **roll back the save** automatically during the application process.

---

## ⚠️ Important Safety Tips

1.  **Close the Game**: Always exit SnowRunner before applying changes. Steam Cloud may conflict with the editor if the game is running.
2.  **Backup Often**: While the tool is safe, keeping an external copy of your `%USERPROFILE%\Documents\My Games\SnowRunner` folder is best practice.
3.  **Reset Behavior**: When you reset a mission, its rewards are removed from your profile. When you re-complete it, they are re-added. This is intended for legitimate replayability.

---

## 🛠️ Troubleshooting

- **"File Not Found"**: Ensure you have selected the terminal folder containing the `.cfg` or `.dat` files.
- **"Access Denied"**: Run the editor as Administrator or check folder permissions.
- **"Steam Cloud Revert"**: If Steam reverts your changes, make sure you edited the files in the `remote/` folder and that the tool updated `remote.vdf` (it does this automatically).
