# Final Absolute Engineering Engine Roadmap (Deterministic Supreme)

This document is the **final, hard-locked engineering contract**. It transitions the project into a **Deterministic, Auditable, Transaction-Safe Game State Engine**. Every action is immutable, versioned, and replayable with a linked dependency chain and human-verifiable intent tracking.

## Core Mandates (The Zero-Shortcut Policy)
1. **Zero-Trust Hydration**: Every byte is verified. `STRICT_MODE = True`.
2. **Immutable Context**: Once hydrated, the `ctx` is logically frozen. No direct mutations allowed.
3. **No Shortcuts**: Never bypass validation, skip dry runs, or mutate outside the transaction layer—even for testing.
4. **Human-Verifiable Audit**: Every operation must have a summary, category, intent, risk level, and ID.
5. **Mirror Testing**: Primary test bed is `E:\Snow Runner New Tool\test_data\steam_live_mirror\`.

---

## Phase 1: Engine Foundation & Zero-Trust Hydration
**Goal:** Establish the verified, immutable "Source of Truth."
- **Data Mirroring:** Script with checksum validation and lock-file skipping.
- **[ENGINE] `engine/exceptions.py`:** `IntegrityError`, `SchemaError`, `BinaryError`, `TransactionError`.
- **[ENGINE] `engine/schema.py` (Versioning):** `SCHEMA_VERSION = "1.0"`. Fail on Required, warn on Optional.
- **[ENGINE] `engine/hydration.py` (Safety Layer):** 
    - Strict `\x00` null enforcement.
    - Encoding Safety: `utf-8` + `errors="replace"` + data loss validation.
    - **Immutable Wrap**: Implement a "frozen" dict/object wrapper for the context.
- **[ENGINE] `engine/slot_resolver.py` (Normalization):** `extract_slot_index()` + `detect_orphans()`.
- **[ENGINE] `engine/metadata.py` & `engine/backups.py`:** Game version detection + 3-stage `.bak1/2/3` rotation.

## Phase 2: Integrity & Ground Truth Audit
**Goal:** Verify the Engine against `remote2` and Live Mirror data.
- **[ENGINE] `engine/compare.py` (Tolerance Rules):** Ignore timestamps/session_ids.
- **[ENGINE] Hash Calibration**: `canonicalize_for_hash()` for stable signatures.
- **Confidence Score:** Report `match_percentage` during comparison.
- **Count Validation:** Registry-driven `expected_maps` verification.

## Phase 3: Game Data Registry
**Goal:** Bidirectional mapping for the "Game Knowledge Repository."
- **Registry:** Universal mapping for regions, maps, and objectives.
- **Bidirectional Normalization:** `Friendly Name <-> String ID` resolving.
- **Drift Detection:** Log `UNKNOWN_ID` during DLC updates.

## Phase 4: Atomic Transactions & Audited Mutations
**Goal:** Safe mutation with human-verifiable diffs and replay capability.
- **[ENGINE] `engine/transaction.py`:** 
    - Slot-level `Operation Lock`.
    - `depends_on` Dependency Chain tracking.
    - **Auto-Snapshot**: Snapshot the current state before applying any change.
    - Pre-Commit Consistency Hook + Bit-level rollback verification.
- **[ENGINE] `engine/simulate.py` (Dry Run):** 
    - Structured `diff.json` (Field: Old -> New).
    - Diff Sanity Check: Prevent unintended side-effects.

## Phase 5: Binary Mastery & Final Interface
**Goal:** Secure ZLIB handling and UI bridging.
- **[ENGINE] `engine/binary_util.py` (Round-Trip):** `decompress -> recompress -> decompress` parity check.
- **Binary Safety Wrapper:** Post-write header and size guardrails.
- **[ENGINE] `engine/audit.py`:** 
    - `audit_log.json` with UUID Operation IDs and Step ID Tracking.
    - **[NEW] Polished Action Summaries**: Human-readable text, `RISK_LEVEL` (LOW/MED/HIGH), **Category** (FINANCIAL/OBJECTIVE/EXPLORATION), **Execution Time (ms)**, and **User Intent Tag**.
- **[ENGINE] Health Check Command:** `run_health_check()` (Grades: Healthy/Warning/Critical).

---

> [!IMPORTANT]
> **Final Strategic Commitment**
> 
> The system is now a **Deterministic Game State Engine**. I will not bypass validation, skip diff checks, or mutate context directly. 
> 
> **Proceed to Phase 1 (Mirroring & Engine Construction)?**
