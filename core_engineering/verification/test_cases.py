# [PH4-VER-004] Verification Test Case Registry (HARDENED)
# [GAP-1] Absolute Boundary Definitions.

TEST_CASES = [
    # 1. VALID MUTATIONS (Happy Path)
    {
        "name": "VALID: Set Money to 50k",
        "field": "player.money",
        "value": 50000,
        "context": {},
        # GAP-1: Explicit allowed change footprint
        "allowed_diff_paths": ["derived.player.money"]
    },
    {
        "name": "VALID: Unlock truck (Cross-Session)",
        "field": "trucks.ws_4964_white.isUnlocked",
        "value": True,
        "context": {"is_cross_session": True},
        # GAP-1: Allow path-globbing for identity-based mutation
        "allowed_diff_paths": ["CompleteSave.SslValue.persistentProfileData.trucksInWarehouse[*].isUnlocked"]
    },

    # 2. INVALID MUTATIONS (Rejection Guard)
    {
        "name": "REJECT: Negative Money Injection",
        "field": "player.money",
        "value": -100,
        "expect_failure": True,
        "allowed_diff_paths": [] # Expect NO changes
    },
    {
        "name": "REJECT: Same-session lock regression",
        "field": "trucks.ws_4964_white.isUnlocked",
        "value": False,
        "context": {"is_cross_session": False},
        "expect_failure": True,
        "allowed_diff_paths": []
    },
    {
        "name": "REJECT: Identity-Resolve failure",
        "field": "trucks.non_existent_truck.isUnlocked",
        "value": True,
        "expect_failure": True,
        "allowed_diff_paths": []
    },

    # 3. BOUNDARY CASES (Stress Limits)
    {
        "name": "BOUNDARY: Zero Money",
        "field": "player.money",
        "value": 0,
        "context": {},
        "allowed_diff_paths": ["derived.player.money"]
    },
    {
        "name": "BOUNDARY: Overflow Money (999M)",
        "field": "player.money",
        "value": 999999999,
        "context": {},
        "allowed_diff_paths": ["derived.player.money"]
    },
    {
        "name": "REJECT: Money Above Max",
        "field": "player.money",
        "value": 1000000001,
        "expect_failure": True,
        "allowed_diff_paths": []
    },

    # 4. SEQUENTIAL LOGIC [PH4-VER-SEQ]
    {
        "name": "SEQUENCE: Multi-step money update",
        "sequence": [
            {"field": "player.money", "value": 1000},
            {"field": "player.money", "value": 2000}
        ],
        "allowed_diff_paths": ["derived.player.money"]
    }
]
