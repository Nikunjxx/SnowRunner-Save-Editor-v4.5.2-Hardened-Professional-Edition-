# Phase 1.1: Core Engine Hardening Plan

This plan addresses the **8 Critical Gaps** found in the Phase 1 Foundation. We will not proceed to Phase 2 until these 100% deterministic layers are verified.

## User Review Required

> [!IMPORTANT]
> **New Execution Rules**
> 1. **Zero Ambiguity**: Schema validation now uses explicit paths (e.g., `SslValue.persistentProfileData.rank`).
> 2. **Derived State**: No raw dictionary access. We provide a flattened, read-only `ctx.derived` layer.
> 3. **Semantic Audit**: We validate not just structure, but gameplay logic (e.g., prevents negative money).
> 4. **Reporting Engine**: Every hydration generates a machine-readable audit report.

---

## Proposed Changes

### [NEW] `engine/report.py`
Integrated report generator that tracks:
- File integrity status.
- Exact missing/invalid fields.
- Schema audit results.
- **Output**: JSON report for the engine, Markdown summary for the user.

### [MODIFY] `engine/schema.py`
Refactor to support **Explicit Path Validation**:
- `REQUIRED_PATHS = {"SslValue.persistentProfileData.money": int}`
- Deep traversal during `validate()`.
- Explicit error reporting per path.

### [NEW] `engine/derived.py`
A read-only abstraction layer that flattens the nested JSON:
- `ctx.player.money` (mapped from `SslValue.persistentProfileData.money`)
- `ctx.progression.maps`

### [NEW] `engine/validator.py`
The "Gameplay Law" layer:
- `validate_semantic(ctx)`
- Check: Money >= 0, Rank in valid range, experience/rank alignment.

### [MODIFY] `engine/hydration.py`
- Integrate `report.py` into `load_all()`.
- Abort on any semantic or schema failure.
- Auto-attach the `DerivedState` to the `FrozenContext`.

---

## Verification Plan

### Automated Tests
- **`engine/test_hardening.py`**:
    - **Immutability Test**: Force-write to `ctx` and assert `AttributeError`.
    - **Schema Test**: Point at a file with a missing path and assert `SchemaError`.
    - **Semantic Test**: Pass -100 money and assert `ValidationError`.
    - **Report Audit**: Verify the generated JSON report accurately reflects the state.

### Manual Verification
- Execute `test_hardening.py` against the **`steam_live_mirror/`** data.
- Present the **Hydration Report** (JSON/MD) for User Review.

## Open Questions

> [!WARNING]
> **Rank Thresholds**: Are there specific "Max Rank" values we should enforce? (e.g., 30 for base game).
