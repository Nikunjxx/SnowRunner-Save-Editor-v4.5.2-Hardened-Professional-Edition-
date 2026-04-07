# Phase 1.2: Supreme Engine Integrity Plan

This document serves as the absolute final blueprint for the **SnowRunner Save Engine** foundation. It incorporates all 9 "Supreme Integrity" guards to ensure the system is 100% deterministic, auditable, and immutable.

## User Review Required

> [!IMPORTANT]
> **Supreme Integrity Mandates**
> 1. **Explicit Pipeline**: No amorphous loading. We enforce (Hydration → Schema → Semantic → Derived → Freeze).
> 2. **State Hash Binding**: Every context is bit-locked with a `ctx.hash` that ignores transient metadata.
> 3. **Mapping Registry**: All derived fields (e.g., `player.money`) are defined in a central `DERIVED_MAP` contract.
> 4. **Idempotency**: All operations must be verified as "already applied" before execution to prevent double-spending or corruption.

---

## Proposed Changes

### [NEW] `engine/pipeline.py`
The orchestration layer that enforces the strict execution order:
1. `hydrate()`: Load raw JSON.
2. `validate_schema(ctx)`: Path-based type/existence check.
3. `validate_semantic(ctx)`: Gameplay logic check (Money >= 0).
4. `build_derived(ctx)`: Flattened access using `DERIVED_MAP`.
5. `freeze(ctx)`: Immutable lock for both raw and derived state.
6. `bind_hash(ctx)`: Attach stable state signature.

### [MODIFY] `engine/schema.py`
Integrated **Schema Migration** placeholder:
- `migrate_schema(old_version, data)`: Transition older save structures to V1.0.
- Enhanced with **Severity Levels** for every validation failure.

### [MODIFY] `engine/report.py`
Enhanced reporting engine:
- Every entry linked to a **Step ID** (e.g., `HYD_001`).
- Included **Severity Classification** (CRITICAL | WARNING | INFO).
- Added `engine_grading`: (HEALTHY / WARNING / CRITICAL).

### [NEW] `engine/idempotency.py`
A shared utility that checks if a change is already present:
- `is_already_applied(operation_id, ctx.hash)`
- `check_drift(current_hash, expected_hash)`

### [MODIFY] `engine/hydration.py`
- Incorporate `FrozenDerivedState` (fully immutable).
- Refactored `load_all()` to use the new `engine/pipeline.py`.

---

## Verification Plan

### Automated Tests
- **`engine/test_supreme_integrity.py`**:
    - **Pipeline Test**: Prove that skipping a stage or out-of-order execution is impossible.
    - **Hash Stability Test**: Change a timestamp and verify the `ctx.hash` remains identical.
    - **Idempotency Test**: Apply the same "set money" action twice and assert the second is ignored.
    - **Immutability Test**: Verify that both `ctx.raw` and `ctx.derived` raise `AttributeError` on mutation.

### Manual Verification
- Execute `test_supreme_integrity.py` against the **`steam_live_mirror/`** data.
- Present the **Supreme Hydration Report** for User Review.

## Open Questions

> [!WARNING]
> **External Changes**: If we detect an external file drift during a transaction, should we **STRICT_STOP** or **AUTO_RELOAD_AND_NOTIFY**? (Recommendation: STRICT_STOP to prevent overwriting cloud-synced data).
