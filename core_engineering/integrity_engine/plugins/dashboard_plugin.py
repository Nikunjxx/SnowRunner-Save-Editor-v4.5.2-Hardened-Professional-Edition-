import tkinter as tk
from tkinter import ttk, messagebox
from typing import Dict, Any, List, Optional
from .base import BasePlugin

class DashboardPlugin(BasePlugin):
    """
    v110.60 Progression Analytics Dashboard Plugin.
    Read-only interface for game state visibility.
    """
    
    def __init__(self):
        self._context = None
        self._frame = None
        self._last_analytics = None
        self._vars = {}

    @property
    def id(self) -> str:
        return "dashboard"

    @property
    def display_name(self) -> str:
        return "📊 Progression"

    @property
    def category(self) -> str:
        return "ADVANCED"

    @property
    def plugin_type(self) -> str:
        return "read"

    @property
    def description(self) -> str:
        return "High-level progression analytics, regional completion stats, and metadata health auditing."

    @property
    def primary_action_name(self) -> str:
        return "Refresh Analytics"

    @property
    def permissions(self) -> Dict[str, Any]:
        return {"read": True}

    def register(self, context: Any):
        self._context = context

    def render(self, parent: tk.Frame):
        """Builds the Dashboard UI."""
        self._frame = ttk.Frame(parent)
        self._frame.pack(fill="both", expand=True)
        self._frame.columnconfigure(0, weight=1)
        self._frame.rowconfigure(1, weight=1)

        # 1. Summary Header
        summary_frame = ttk.LabelFrame(self._frame, text=" Global Progression Summary ", padding=15)
        summary_frame.grid(row=0, column=0, sticky="ew", padx=10, pady=10)
        
        metrics = [
            ("Total Completion", "perc_var", "%"),
            ("Total XP Earned", "xp_earned_var", ""),
            ("Total Money Earned", "money_earned_var", "¢")
        ]
        
        for label, var_name, unit in metrics:
            f = ttk.Frame(summary_frame)
            f.pack(side="left", expand=True, fill="x")
            ttk.Label(f, text=label, font=("Segoe UI", 9)).pack()
            var = tk.StringVar(value="--")
            self._vars[var_name] = var
            lbl = ttk.Label(f, textvariable=var, font=("Segoe UI", 16, "bold"), foreground="#2ecc71")
            lbl.pack()
            if unit: ttk.Label(f, text=unit, font=("Segoe UI", 8)).pack()

        # 2. Regional Breakdown Table
        table_frame = ttk.LabelFrame(self._frame, text=" Regional Breakdown ", padding=10)
        table_frame.grid(row=1, column=0, sticky="nsew", padx=10, pady=5)
        
        columns = ("region", "completed", "total", "perc", "xp_pot", "money_pot")
        self.tree = ttk.Treeview(table_frame, columns=columns, show="headings", height=10)
        self.tree.heading("region", text="Region Name")
        self.tree.heading("completed", text="Completed")
        self.tree.heading("total", text="Total Cataloged")
        self.tree.heading("perc", text="Percentage")
        self.tree.heading("xp_pot", text="XP Potential")
        self.tree.heading("money_pot", text="Money Potential")
        self.tree.pack(side="left", fill="both", expand=True)
        
        sb = ttk.Scrollbar(table_frame, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=sb.set)
        sb.pack(side="right", fill="y")

        # 3. Bottom Panels
        bottom_frame = ttk.Frame(self._frame)
        bottom_frame.grid(row=2, column=0, sticky="ew", padx=10, pady=10)
        bottom_frame.columnconfigure(0, weight=1)
        bottom_frame.columnconfigure(1, weight=1)

        # 3.1 Type Distribution
        dist_frame = ttk.LabelFrame(bottom_frame, text=" Objective Classification ", padding=10)
        dist_frame.grid(row=0, column=0, sticky="nsew", padx=(0, 5))
        self._vars["world_var"] = tk.StringVar(value="🌏 World: 0 / 0")
        self._vars["logical_var"] = tk.StringVar(value="💰 Logical: 0 / 0")
        ttk.Label(dist_frame, textvariable=self._vars["world_var"], font=("Segoe UI", 10)).pack(anchor="w", pady=2)
        ttk.Label(dist_frame, textvariable=self._vars["logical_var"], font=("Segoe UI", 10)).pack(anchor="w", pady=2)

        # 3.2 Metadata Audit
        audit_frame = ttk.LabelFrame(bottom_frame, text=" ⚠️ Metadata Health Audit ", padding=10)
        audit_frame.grid(row=0, column=1, sticky="nsew", padx=(5, 0))
        self._vars["unknown_count_var"] = tk.StringVar(value="Metadata Gaps: 0 items detected")
        ttk.Label(audit_frame, textvariable=self._vars["unknown_count_var"], foreground="#e67e22", font=("Segoe UI", 10, "bold")).pack(anchor="w")
        self.gap_btn = ttk.Button(audit_frame, text="View Gaps", command=self._show_unknowns, state="disabled")
        self.gap_btn.pack(side="right", pady=5)

        self.refresh()

    def refresh(self):
        """Fetches data via the PluginContext."""
        if not self._context or not self._frame:
            return
            
        try:
            analytics = self._context.get_progression_data(self)
            self._last_analytics = analytics
            
            # Update Vars
            t = analytics["totals"]
            self._vars["perc_var"].set(f"{t['perc']}%")
            self._vars["xp_earned_var"].set(f"{t['xp_earned']:,}")
            self._vars["money_earned_var"].set(f"{t['money_earned']:,}")
            self._vars["world_var"].set(f"🌏 World: {t['world_completed']} / {t['world_total']}")
            self._vars["logical_var"].set(f"💰 Logical: {t['logical_completed']} / {t['logical_total']}")
            
            u_count = len(analytics["unknown_in_save"])
            self._vars["unknown_count_var"].set(f"Metadata Gaps: {u_count} items")
            self.gap_btn.configure(state="normal" if u_count > 0 else "disabled")

            # Update Table
            self.tree.delete(*self.tree.get_children())
            for r_name, reg in sorted(analytics["regions"].items()):
                self.tree.insert("", "end", values=(
                    r_name, reg["completed"], reg["total"], 
                    f"{reg['perc']}%", f"+{reg['xp_potential']:,}", f"+{reg['money_potential']:,}¢"
                ))
        except Exception as e:
            print(f"[DashboardPlugin] Refresh failed: {e}")

    def on_folder_load(self, folder_path: str):
        self.refresh()

    def execute(self, context: Any) -> Dict[str, Any]:
        """Primary action: Force refresh of analytics."""
        try:
            self.refresh()
            return {"success": True, "summary": "Progression analytics refreshed."}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def _show_unknowns(self):
        if not self._last_analytics: return
        unknowns = self._last_analytics.get("unknown_in_save", [])
        msg = "Unknown Objective IDs in save:\n\n" + "\n".join([f"• {u}" for u in unknowns[:15]])
        if len(unknowns) > 15: msg += f"\n... and {len(unknowns)-15} more."
        messagebox.showinfo("Metadata Gaps", msg)
