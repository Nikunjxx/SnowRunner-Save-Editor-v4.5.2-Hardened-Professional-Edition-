import tkinter as tk
from typing import Dict, Any, List, Optional
from .base import BasePlugin

class ProgressionModifierPlugin(BasePlugin):
    """
    v114.00 Progression Modifier Plugin.
    Provides WRITABLE interface for Money, Rank, and XP.
    """
    
    def __init__(self):
        self._context = None
        self._frame = None
        self._vars = {}

    @property
    def id(self) -> str:
        return "progression_modifier"

    @property
    def display_name(self) -> str:
        return "💰 Bank & Rank"

    @property
    def category(self) -> str:
        return "CORE"

    @property
    def plugin_type(self) -> str:
        return "write"

    @property
    def description(self) -> str:
        return "Modify player currency, global rank, and experience points directly."

    @property
    def primary_action_name(self) -> str:
        return "Save Progression Changes"

    @property
    def permissions(self) -> Dict[str, Any]:
        return {"read": True, "write": True}

    def register(self, context: Any):
        self._context = context

    def render(self, parent: tk.Frame):
        """Builds the Modifier UI."""
        from tkinter import ttk
        self._frame = ttk.Frame(parent, padding=20)
        self._frame.pack(fill="both", expand=True)

        header = ttk.Label(self._frame, text=" Progression Editor ", font=("Segoe UI", 14, "bold"))
        header.pack(pady=(0, 20))

        # 1. Money Editor
        money_frame = ttk.LabelFrame(self._frame, text=" Player Currency ", padding=15)
        money_frame.pack(fill="x", pady=10)
        ttk.Label(money_frame, text="Total Money: ").pack(side="left")
        self._vars["money"] = tk.StringVar(value="0")
        ttk.Entry(money_frame, textvariable=self._vars["money"], width=20).pack(side="left", padx=5)

        # 2. Rank Editor
        rank_frame = ttk.LabelFrame(self._frame, text=" Global Rank & XP ", padding=15)
        rank_frame.pack(fill="x", pady=10)
        
        ttk.Label(rank_frame, text="Rank: ").grid(row=0, column=0, sticky="w")
        self._vars["rank"] = tk.StringVar(value="1")
        ttk.Entry(rank_frame, textvariable=self._vars["rank"], width=10).grid(row=0, column=1, sticky="w", padx=5, pady=5)

        ttk.Label(rank_frame, text="Total XP: ").grid(row=1, column=0, sticky="w")
        self._vars["xp"] = tk.StringVar(value="0")
        ttk.Entry(rank_frame, textvariable=self._vars["xp"], width=15).grid(row=1, column=1, sticky="w", padx=5, pady=5)

        ttk.Separator(self._frame, orient="horizontal").pack(fill="x", pady=20)
        ttk.Label(self._frame, text="⚠️ Note: Any changes made here are permanent once saved.", foreground="#e67e22", font=("Segoe UI", 9, "italic")).pack()

        self.refresh()

    def refresh(self):
        """Fetches data via the PluginContext."""
        if not self._context or not self._frame: return
        
        try:
             player = self._context.save_context["player"]
             self._vars["money"].set(str(player["money"]))
             self._vars["rank"].set(str(player["rank"]))
             self._vars["xp"].set(str(player["experience"]))
        except Exception as e:
             print(f"[ProgressionModifier] Refresh failed: {e}")

    def on_folder_load(self, folder_path: str):
        self.refresh()

    def execute(self, context: Any) -> Dict[str, Any]:
        """Primary action: Commit changes to the save file."""
        try:
             money = int(self._vars["money"].get())
             rank = int(self._vars["rank"].get())
             xp = int(self._vars["xp"].get())
             
             success = context.update_player_stats(money, rank, xp)
             if success:
                 return {"success": True, "summary": f"Progression updated: ${money:,} / Rank {rank}."}
             else:
                 return {"success": False, "error": "Failed to locate or update the player save file."}
        except ValueError:
             return {"success": False, "error": "Please enter valid numeric values for all fields."}
        except Exception as e:
             return {"success": False, "error": str(e)}
