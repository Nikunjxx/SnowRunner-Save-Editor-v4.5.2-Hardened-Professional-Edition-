# SnowRunner Save Editor (Hardened Professional Edition)

A mission-critical, high-performance save editor for SnowRunner, designed with absolute data integrity and user safety as core technical invariants.

## 🚀 Mission: Safety First
This editor is not just a tool; it is a **Hardened Control Surface**. Built upon a multi-layered engineering architecture, it guarantees that your save files remain uncorrupted through every mutation cycle.

### Core Technical Invariants
- **Atomic Transactions**: Uses a Backup-Write-Validate-Commit pattern. If a write fails, the system restores your original save files instantly.
- **Zero-Trust Validation**: Every mutation is gated by a rigorous FieldValidator layer. Illegal values are rejected before they ever reach the disk.
- **Mission Observability**: Every action is recorded in machine-parseable JSON logs, providing a 100% transparent audit trail of your session.
- **State Restoration**: A centralized RecoveryManager ensures that even a failed UI operation results in a perfect restoration of the engine state.
- **High Performance**: Optimized with Dirty-Path Checkpointing and Identity-Based Fast Diffing for a responsive, lag-free experience.

## 🛠️ Features
- **Player Progression**: Modernize money, rank, and experience with safety-checked adjustment gates.
- **Warehouse Management**: Identity-based truck unlocking. No risk of index-drift or positional corruption.
- **Upgrade Discovery**: Resolves game-logic registries to reveal and install upgrades safely.
- **Self-Healing**: Automated failure handling with user-safe error translation.

## 📦 Usage
1. **Launch**: Run `SnowRunnerEditor.exe`.
2. **Load**: Select your `CompleteSave.cfg` (Steam) or `.dat` (Epic/MS Store) file.
3. **Edit**: Modify your progress using the intuitive, tabbed interface.
4. **Commit**: Click "Save Changes". The application will perform an atomic commit and notify you of success.

## 📁 Project Structure
- `core_engineering/`: The mission-critical engine, transaction, and verification logic.
- `ui/`: The high-fidelity, tab-aware control surface.
- `logs/`: Continuous session telemetry.

## ⚖️ License
Distributed under the MIT License. See `LICENSE` for more information.
