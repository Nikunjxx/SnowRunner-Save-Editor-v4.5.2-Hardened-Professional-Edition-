# [PH3-UI-010] Player Stats Panel (REFINED v2)
import tkinter as tk
from tkinter import ttk, messagebox

class PlayerPanel:
    """
    Control Layer for Player Stats.
    REFINEMENTS:
    - Two-Stage Value System (display vs edit buffer).
    - Validation-First Commit loop.
    - Automated re-render after engine update.
    """
    
    def __init__(self, parent, mapper, validator, on_apply_callback):
        self.parent = parent
        self.mapper = mapper
        self.validator = validator
        self.on_apply_callback = on_apply_callback # Link to MainWindow pipeline
        
        # Identity-Locked Variables (Rule: State-free storage)
        self.money_display = tk.StringVar()
        self.rank_display = tk.StringVar()
        self.xp_display = tk.StringVar()
        
        # [REFINEMENT 1] Edit Buffer (The 'Input' layer)
        self.money_buffer = tk.StringVar()
        
        self._setup_view()

    def _setup_view(self):
        """Builds static layout with refined two-stage fields."""
        frame = ttk.LabelFrame(self.parent, text="Player Progression", padding=10)
        frame.pack(fill="x", padx=10, pady=10)
        
        # Money (Two-Stage: Current vs New)
        ttk.Label(frame, text="Current Money:").grid(row=0, column=0, sticky=tk.W)
        ttk.Label(frame, textvariable=self.money_display).grid(row=0, column=1, sticky=tk.W, padx=5)
        
        ttk.Label(frame, text="Enter New Amount:").grid(row=1, column=0, sticky=tk.W)
        self.money_entry = ttk.Entry(frame, textvariable=self.money_buffer)
        self.money_entry.grid(row=1, column=1, sticky=tk.W, padx=5)
        ttk.Button(frame, text="Apply & Resolve", command=self._on_apply_money).grid(row=1, column=2)
        
        # Rank/XP (Read-Only per architecture rules)
        ttk.Separator(frame, orient='horizontal').grid(row=2, column=0, columnspan=3, sticky="ew", pady=10)
        
        ttk.Label(frame, text="Resolved Rank:").grid(row=3, column=0, sticky=tk.W)
        ttk.Label(frame, textvariable=self.rank_display).grid(row=3, column=1, sticky=tk.W, padx=5)
        
        ttk.Label(frame, text="Resolved XP:").grid(row=4, column=0, sticky=tk.W)
        ttk.Label(frame, textvariable=self.xp_display).grid(row=4, column=1, sticky=tk.W, padx=5)

    def render(self, resolved_player_data: dict):
        """
        [REFINEMENT 3] Populates UI with resolved state from Bridge Mapper.
        Ensures UI always displays the 'Absolute Truth' from the absolute engine.
        """
        self.money_display.set(str(resolved_player_data.get("money", 0)))
        self.rank_display.set(str(resolved_player_data.get("rank", 1)))
        self.xp_display.set(str(resolved_player_data.get("experience", 0)))
        
        # Clear buffer after successful resolution to match display
        self.money_buffer.set("")

    def _on_apply_money(self):
        """SAFE EDIT PIPELINE: Monetary Adjustment."""
        new_value = self.money_buffer.get()
        
        # [PH4-EXEC-GATED] No manual validation. 
        # Rely on SafeExecutor + ValidationRegistry in the Engine.
        self.on_apply_callback("player.money", int(new_value))
