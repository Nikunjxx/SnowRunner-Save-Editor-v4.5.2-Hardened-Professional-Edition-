# SnowRunner Save Editor - User Guide

Welcome to the **SnowRunner Save Editor**, a lightweight GUI tool for modifying your SnowRunner game progress. This guide explains how to use the editor safely and effectively.

---

## 🛡️ Safety First: Backups
The first and most important step is ensuring your save data is safe.
- **Auto-Backup**: The editor creates a backup every time you modify a save file. You can manage these in the **Backups** tab.
- **Manual Recommendation**: Before using any save editor, always keep a manual copy of your `CompleteSave.cfg` in a separate folder.

## 🚀 Getting Started
1. **Locate your save file**: The editor usually remembers your last file. In the **Save File** tab, browse for your `CompleteSave.cfg`.
2. **One-Click Standalone**: You can move the `.exe` anywhere. It does **not** require Python, redistributables, or any other pre-requisites.
3. **Reload**: If you make changes in-game while the editor is open, the tool will often auto-refresh, but you can always click **Reload** to be safe.


---

## 🛠️ Feature Highlights

### 🏠 Garages & The Recovery Fix
The **Garages** tab allows you to unlock regional garages instantly.
- **Unlock Garages**: Grants immediate access to garages in selected regions.
- **❤️ Fix Recovery System**: 
    > [!IMPORTANT]
    > If you previously used a version of this tool (or others) that broke your in-game "Recover" button, use this feature. It repairs the save by registering the "entrance zones" that the game requires to teleport your vehicle.

### 💰 Money & Rank
Easily adjust your funds and player level to skip the grind or experiment with expensive truck builds. 

### 🌄 Time & Environment
Adjust the in-game clock, freeze time at noon for visibility, or change game rules like fuel consumption and repair costs.

### 🗺️ Regions+ (Map Discovery)
A comprehensive tool to manage multiple regions at once. 
- **Reveal Map (Reveal Fog)**: Generates a fully cleared fog file for the map. Use this to instantly remove the "clouds" from the map even for locations you haven't visited yet.
- **Discover Trucks/Trailers**: Scans the map for all hidden vehicles and trailers. Marking them "Discovered" allows you to switch to them or use the **Recover** button immediately from the Global Map.
- **Unlock Watchtowers**: Marks all towers as found on the map.
- **❤️ Fix Recovery System**: 
    > [!IMPORTANT]
    > If you previously used a version of this tool (or others) that broke your in-game "Recover" button, use this feature. It repairs the save by registering the "entrance zones" as a list in your save file.

### 🏗️ Objectives+ (Missions)
A powerful batch-editor for missions. You can mark all missions in a region (or the whole game) as "Found," "Accepted," or "Completed" in a single click. 
- **Select All Filtered**: Use the new checkbox to quickly select every visible mission in your current search filter for bulk completion.
- **Complete Tasks**: Renamed for clarity. Select your tasks and click this to finish them instantly.
> [!TIP]
> Use this to skip a tedious mission that is blocking your progress without affecting other map data.

### 🚛 Vehicles (STS)
The only tool that allows you to physically move trucks on the map. 
- **Unstuck (+Y)**: Lifts the truck up. Use this if your vehicle is clipped into a bridge or the ground.
- **Custom XYZ**: Teleport your selected truck to any coordinate on the map.
- **Delete**: Permanently remove a glitched or unwanted vehicle from the map state.

### 🗂️ Save Profiler & Slot Cloner
Manage your game profiles across the 4 available slots.
- **Clone Progress**: Safely copy your career progress from Slot 1 to Slot 2, 3, or 4.
- **Backup Profile**: Create isolated backups of specific save slots for safe-keeping.

### 🏪 Truck Emporium (Vehicles Store)
The ultimate vehicle management suite for **Seasons 1-17**.
- **🛍️ Store Unlock**: Select any truck and mark it for "Store Unlock." The editor uses **Smart-Sync** to automatically unlock the truck’s unique specialized parts (engines, cranes, etc.) and bypass map-discovery locks.
- **🚀 Global Injector**: Spawn any truck directly into your garage storage for free.
- **📊 Detailed Info**: View the origin region and the original mission required for every truck.


---

## ❓ Troubleshooting

### "Fix Recovery doesn't work after I unlocked a garage!"
Some garages are "quest-gated" (like the one in Amur – Chernokamensk). Even if it is unlocked in the save, you may still need to complete the opening mission for the physical entrance to appear.

### "Antivirus flagged the .exe!"
This is common for Python applications compiled with PyInstaller. The editor is open-source — you can review the code on GitHub if you are concerned.

---

## ☕ Support the Project
If this tool helped you save your progress or skip a tedious grind, consider saying thanks!
[GitHub Repository](https://github.com/Nikunjxx/NextGen-SnowRunner-Editor)

*Made with 🛠️ by Nikunjxx*
