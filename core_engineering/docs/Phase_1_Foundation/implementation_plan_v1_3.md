# Phase 1.3: Deterministic Supreme Engine (Ultra-Hardened Edition)

This document is the **final, hard-locked engineering contract** for the **SnowRunner Save Engine** foundation. It transitions the project into a **Deterministic, Transaction-Safe, Path-Aware Game State Engine**. No further architectural changes are permitted after this phase begins.

## User Review Required

> [!IMPORTANT]
> **Supreme Integrity Final Commitments**
> 1. **Prefix-Safe Path Canonicalization**: We protect progression order using exact matching or prefix-safe logic (`path == p` or `path.startswith(p + ".")`). This prevents accidental sorting of similar nested structures.
> 2. **Hash & Engine Versioning**: Every context is tagged with `hash_version="v1"`, `schema_version="1.0"`, and `engine_version="1.3"`.
> 3. **Fail-Safe Locking**: Every pipeline execution uses `try/finally` for guaranteed slot-lock release.
> 4. **Conflict Resolution Matrix**: Hard-coded truth table in `engine/rules.py` handles Validation vs. Intent overlaps.

---

## Proposed Changes

### [MODIFY] `engine/mapping.py`
Enhanced mapping and path constants:
- `DERIVED_MAP` / `REVERSE_MAP` (One-to-One).
- **[NEW] `ORDER_SENSITIVE_PATHS`**: Registry of JSON paths where list order must be preserved.

### [MODIFY] `engine/debug.py` (The Hash Engine)
- **`canonicalize(data, path="")`**: 
    - Recursive traversal of dicts (sorted keys).
    - **Ultra-Precise Matching**:
      ```python
      def is_order_sensitive(current_path):
          return any(current_path == p or current_path.startswith(p + ".") 
                     for p in ORDER_SENSITIVE_PATHS)
      ```
    - Final bit-stream generation for SHA-256.

### [NEW] `engine/rules.py` (Conflict Resolution)
The definitive Truth Table for validation vs. operational intent:
| Validation Severity | Intent Severity | Result |
| :--- | :--- | :--- |
| **STRICT** | ANY | **ABORT** (Always) |
| **CRITICAL** | ANY | **ABORT** (Always) |
| **WARNING** | **NORMAL** | **PROCEED** (With Caution) |
| **WARNING** | **STRICT** | **ABORT** (Intent-specific safety) |
| **INFO** | ANY | **PROCEED** (Informational only) |

### [MODIFY] `engine/report.py` (The Verdict)
- **Metadata Expansion**: Includes `engine_version`, `schema_version`, and `hash_version`.
- **Hash Visibility**: Exposes `ctx_hash` in the final diagnostic report.

### [MODIFY] `engine/pipeline.py` (The Singleton)
- **Safe Execution Pattern**: `try/finally` with `LOCK_REGISTRY`.
- **Strict Ordering**: `_freeze()` → `_canonicalize(with_prefix_protection)` → `_compute_hash()`.

---

## 🌎 Reality Check (Final Strategic Commitment)
From this point forward, the Architecture is considered **Perfect**. 
Failures will no longer stem from the engine's design, but from:
1. **Incorrect DERIVED_MAP paths** (Human mapping error).
2. **Game-specific quirks** (SnowRunner save format inconsistencies).
3. **Unexpected data combinations** (Modded edge-cases).
4. **DLC/Version drift** (Schema changes in future updates).

---

## Verification Plan

### Automated Tests
- **`engine/test_supreme_ultimate.py`**:
    - **Path Matching Precision**: Verify that `missions.sequence` is protected while `missions.sequence_extra` (if not in registry) remains deterministically sorted.
    - **Crash Recovery**: Verify the slot lock is released after an intentional pipeline crash.
    - **Hash Stability**: Verify that `v1` hashing ignores transient metadata but catches structural data changes.

### Manual Verification
- Execute against the **`steam_live_mirror/`** data.
- Present the **First Supreme Ultimate Hydration Report** for User Sign-off.
