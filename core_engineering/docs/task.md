# Master Engineering Checklist (SnowRunner Save Engine)

## Phase 1: Engine Foundation & Zero-Trust Hydration
- [x] **Data Mirroring & Checksums**
    - [x] Create `mirror_live_data.py`.
    - [x] [HARD] Implement checksum-based validation and skip-locked-files logic.
- [x] **Exception Layer (`engine/exceptions.py`)** [PH1-EXC-001]
- [x] **Canonical Schema Contract (`engine/schema.py`)** [PH1-SCH-001]
- [x] **Strict Slot Resolver (`engine/slot_resolver.py`)** [PH1-SLO-001]
- [x] **Safety Hydration (`engine/hydration.py`)** [PH1-HYD-001]
- [x] **Detection, Snapshots & Backups** [PH1-DET-001]
    - [x] [HARD] `engine/metadata.py`: Game build detection.
    - [x] [HARD] `engine/debug.py`: Versioned snapshots & deterministic sorting.
    - [x] [HARD] Implement `@profile_step` timing decorator.
    - [x] [HARD] Create `backups.py` with `.bak1/2/3` rotation.

## Phase 1.3: Deterministic Supreme Engine (COMPLETED)
- [x] **Explicit Pipeline (`engine/pipeline.py`)** 
    - [x] [HARD] Enforce (Hydrate -> Schema -> Semantic -> Freeze -> Hash).
    - [x] [HARD] **Fail-Safe Locking**: `try/finally` with `LOCK_REGISTRY`.
- [x] **State Hash Binding**
    - [x] [HARD] Implement `_compute_hash()` strictly *after* **prefix-safe** path canonicalize.
    - [x] [HARD] Attach `ctx.hash` and `hash_version="v1"` to the context and report.
    - [x] [HARD] Define `HASH_EXCLUDE_PATHS`.
- [x] **Derived Mapping Contract (`engine/mapping.py`)**
    - [x] [HARD] One-to-one constraint: `assert len(set(REVERSE_MAP.values())) == len(REVERSE_MAP)`.
    - [x] [HARD] **Prefix-Safe Path Awareness**: Define `ORDER_SENSITIVE_PATHS`.
- [x] **Idempotency & Drift Detection (`engine/idempotency.py`)** 
    - [x] [HARD] **Composite Intent Aware**: State-based multi-field check.
- [x] **Advanced Reporting Engine (`engine/report.py`)**
    - [x] [HARD] Implement **Severity Grading** (CRITICAL | WARNING | INFO | STRICT).
    - [x] [HARD] Supreme High-Resolution Metrics (Total Time + Stage %).

## Phase 2: Compare & Ground Truth Engine (v2.2 — HARDENED) [APPROVED]
- [/] [NEW] **CompareEngine**: Deep-path structural diff (`compare.py`)
    - [ ] [HARD] Canonical Comparison Only: `compare(ctx_a.canonical, ctx_b.canonical)`.
    - [ ] [HARD] Strict Format: `{path, value_a, value_b, type, severity, classification, confidence_impact}`.
- [ ] [NEW] **NoiseFilter**: Standardized transient exclusion (`noise_filter.py`)
    - [ ] [HARD] Pattern-based matching (`runtime.*`, `*.timestamp`).
- [ ] [NEW] **Classifier**: Semantic diff classification (`classifier.py`)
    - [ ] [HARD] Logic: Maps mismatches to `EXPECTED_DELTA` vs `VALUE_MISMATCH`.
- [ ] [NEW] **Consistency Auditor**: Cross-file validation (`consistency.py`)
    - [ ] [HARD] `GROUND_TRUTH_MATRIX`: `rank` in `CompleteSave` vs. `achievementStates` in `CommonSslSave`.
- [ ] [NEW] **ConfidenceScorer**: Weighted trust metrics (`scorer.py`)
    - [ ] [HARD] Weights: `STRICT` (5), `OPTIONAL` (1).
- [ ] [NEW] **Ground Truth Audit**: Master diagnostic script (`scripts/ground_truth_audit.py`)

## Phase 3: Game Data Registry (UPCOMING)
- [ ] **Unified Game DB**
    - [ ] [HARD] Bidirectional Normalization: `Friendly Name <-> String ID`.
    - [ ] [HARD] Registry Drift Detection (Log `UNKNOWN_ID`).

## Phase 4: Atomic Transactions & Simulation (UPCOMING)
- [ ] **Transaction Manager (`engine/transaction.py`)**
    - [ ] [HARD] `Operation Lock` (Scope level).
    - [ ] [HARD] Pre-Commit Consistency Hook.
    - [ ] [HARD] Auto-Snapshot: `snapshot_ctx()` before every transaction attempt.
    - [ ] [HARD] Rollback Verification (byte-level assertion after restore).
- [ ] **Simulation Shell (`engine/simulate.py`)**
    - [ ] [HARD] Structured `diff.json` (Old -> New).
- [ ] **Replay Utility (`engine/replay.py`)**
    - [ ] [HARD] `Replay Dry-Run Mode`: `replay(..., simulate=True)`.

## Phase 5: Binary Mastery & Final Interface
- [ ] **Binary Safety (`engine/binary_util.py`)**
    - [ ] [HARD] Round-Trip Validation (decompress -> recompress -> decompress).
- [ ] **Audit & Shell**
    - [ ] [HARD] `audit_log.json` with UUID Operation IDs and Step ID Tracking.
    - [ ] [HARD] `run_health_check()` command.
