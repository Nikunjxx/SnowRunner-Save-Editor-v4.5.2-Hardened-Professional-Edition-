import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from typing import Dict, Any, List, Optional, Set
from .base import BasePlugin

class VehicleInspectorPlugin(BasePlugin):
    """
    v110.80 hardened Vehicle Inspector Plugin.
    Provides high-fidelity, read-only auditing of vehicles across all regions.
    """
    
    def __init__(self):
        self._context = None
        self._frame = None
        self._vars = {
            "external_path": None,
            "summary": None,
            "filter_region": None,
            "filter_state": None,
            "deep_metrics": None
        }
        self._last_data = {}
        self._external_data = None
        self._failed_maps = set()

    @property
    def id(self) -> str:
        return "vehicle_inspector"

    @property
    def display_name(self) -> str:
        return "🚚 Vehicle Inspector"

    @property
    def category(self) -> str:
        return "INTELLIGENCE"

    @property
    def plugin_type(self) -> str:
        return "read"

    @property
    def description(self) -> str:
        return "Batch fog reveal for explored maps. Removes the fog of war from traversing maps without affecting mission progression or game stats."

    @property
    def primary_action_name(self) -> str:
        return "Refresh Vehicle Audit"

    @property
    def permissions(self) -> Dict[str, Any]:
        return {"read": True, "write": False}

    def register(self, context: Any):
        self._context = context
        self._vars["external_path"] = tk.StringVar(value="")
        self._vars["summary"] = tk.StringVar(value="Select an external save folder to compare vehicle states.")
        self._vars["filter_region"] = tk.StringVar(value="All Regions")
        self._vars["filter_state"] = tk.StringVar(value="All States")
        self._vars["deep_metrics"] = tk.BooleanVar(value=False)

    def render(self, parent: tk.Frame):
        self._frame = ttk.Frame(parent, padding=15)
        self._frame.pack(fill="both", expand=True)
        
        # 1. Comparison Header
        comp_frame = ttk.LabelFrame(self._frame, text=" Comparison Target (B) ", padding=10)
        comp_frame.pack(fill="x", pady=(0, 10))
        
        ttk.Label(comp_frame, text="Folder:").pack(side="left")
        ttk.Entry(comp_frame, textvariable=self._vars["external_path"], width=50).pack(side="left", padx=5)
        ttk.Button(comp_frame, text="Browse...", command=self._on_browse).pack(side="left")
        ttk.Button(comp_frame, text="Compare Now", command=self.refresh).pack(side="right")

        # 2. Summary Deltas
        self.summary_frame = ttk.LabelFrame(self._frame, text=" 📊 Vehicle Discovery Deltas ", padding=10)
        self.summary_frame.pack(fill="x", pady=(0, 10))
        
        self.lbl_summary = ttk.Label(self.summary_frame, text="Vehicles: -- | + Added: -- | - Removed: -- | ↔ Moved: --", font=("Segoe UI", 10, "bold"))
        self.lbl_summary.pack(anchor="w")
        
        self.lbl_failed = ttk.Label(self.summary_frame, text="", foreground="orange", font=("Segoe UI", 9, "italic"))
        self.lbl_failed.pack(anchor="w")

        # 3. Filters
        filter_frame = ttk.Frame(self._frame)
        filter_frame.pack(fill="x", pady=(0, 5))
        
        ttk.Label(filter_frame, text="Region:").pack(side="left")
        self.cb_region = ttk.Combobox(filter_frame, textvariable=self._vars["filter_region"], state="readonly", width=20)
        self.cb_region.pack(side="left", padx=5)
        self.cb_region.bind("<<ComboboxSelected>>", lambda e: self._update_table())
        
        ttk.Label(filter_frame, text="State:").pack(side="left", padx=(10, 0))
        self.cb_state = ttk.Combobox(filter_frame, textvariable=self._vars["filter_state"], values=["All States", "garage", "deployed", "unknown"], state="readonly", width=15)
        self.cb_state.pack(side="left", padx=5)
        self.cb_state.bind("<<ComboboxSelected>>", lambda e: self._update_table())
        
        ttk.Checkbutton(filter_frame, text="Deep Metrics (Fuel/Damage)", variable=self._vars["deep_metrics"], command=self._update_table).pack(side="right")

        # 4. Results Table
        table_frame = ttk.Frame(self._frame)
        table_frame.pack(fill="both", expand=True)
        
        cols = ("id", "map", "state", "fuel", "damage")
        self.tree = ttk.Treeview(table_frame, columns=cols, show="headings", height=15)
        self.tree.heading("id", text="Vehicle ID")
        self.tree.heading("map", text="Current Map")
        self.tree.heading("state", text="State")
        self.tree.heading("fuel", text="Fuel")
        self.tree.heading("damage", text="Damage")
        
        self.tree.column("id", width=250)
        self.tree.column("map", width=150)
        self.tree.column("state", width=80)
        self.tree.column("fuel", width=80)
        self.tree.column("damage", width=80)
        
        self.tree.pack(side="left", fill="both", expand=True)
        
        sb = ttk.Scrollbar(table_frame, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=sb.set); sb.pack(side="right", fill="y")
        
        # Tags for diff highlighting
        self.tree.tag_configure('added', foreground='green')
        self.tree.tag_configure('removed', foreground='red')
        self.tree.tag_configure('moved', foreground='blue')
        self.tree.tag_configure('state_changed', foreground='orange')

        self.refresh()

    def _on_browse(self):
        path = filedialog.askdirectory(title="Select External Save Folder (B)")
        if path:
            self._vars["external_path"].set(path)
            self.refresh()

    def refresh(self):
        if not self._context or not self._frame: return
        
        try:
            # 1. Fetch current snapshot (A)
            snap_a = self._context.get_active_snapshot(self)
            self._last_data = snap_a.get("vehicles", {}) if snap_a else {}
            self._failed_maps = snap_a.get("metadata", {}).get("failed_sts", set()) if snap_a else set()
            
            # 2. Handle External Comparison (B)
            ext_path = self._vars["external_path"].get()
            if ext_path and ext_path != self._context.save_folder:
                res_b = self._context.peek_external_save(ext_path, self)
                if "error" not in res_b:
                    self._external_data = res_b.get("vehicles", {})
                else:
                    self._external_data = None
                    messagebox.showwarning("Comparison Error", res_b["error"])
            else:
                self._external_data = None
            
            # 3. Update UI
            self._update_filters()
            self._update_table()
            
        except Exception as e:
            print(f"[VehicleInspector] Refresh failed: {e}")

    def _update_filters(self):
        maps = set()
        for v in self._last_data.values(): 
            if v.get("map"): maps.add(v["map"])
        if self._external_data:
            for v in self._external_data.values():
                if v.get("map"): maps.add(v["map"])
        
        self.cb_region["values"] = ["All Regions"] + sorted(list(maps))

    def _update_table(self):
        if not self.tree: return
        self.tree.delete(*self.tree.get_children())
        
        data_a = self._last_data
        data_b = self._external_data
        
        # Deep Metrics Visibility
        show_deep = self._vars["deep_metrics"].get()
        if show_deep:
            self.tree.column("fuel", width=80); self.tree.column("damage", width=80)
        else:
            self.tree.column("fuel", width=0); self.tree.column("damage", width=0)
            
        # Failed maps badge
        if self._failed_maps:
             self.lbl_failed.config(text=f"⚠️ {len(self._failed_maps)} maps skipped due to parse errors.")
        else:
             self.lbl_failed.config(text="")

        if data_b:
            self._render_comparison(data_a, data_b)
        else:
            self._render_standalone(data_a)

    def _render_standalone(self, data):
        f_reg = self._vars["filter_region"].get()
        f_state = self._vars["filter_state"].get()
        
        # Sort by (map, id)
        sorted_keys = sorted(data.keys(), key=lambda k: (data[k].get("map") or "", k))
        
        count = 0
        for vid in sorted_keys:
            v = data[vid]
            if f_reg != "All Regions" and v.get("map") != f_reg: continue
            if f_state != "All States" and v.get("state") != f_state: continue
            
            # Display strip map-scoped key for UI (vid is "id::map")
            display_id = vid.split("::")[0]
            
            self.tree.insert("", "end", values=(
                display_id, v.get("map", "Unknown"), v.get("state", "unknown"),
                f"{v.get('fuel')}" if v.get('fuel') is not None else "--",
                f"{v.get('damage')}" if v.get('damage') is not None else "--"
            ))
            count += 1
        
        self.lbl_summary.config(text=f"Vehicles: {count} total")

    def _render_comparison(self, a, b):
        keys_a = set(a.keys())
        keys_b = set(b.keys())
        
        added = keys_b - keys_a
        removed = keys_a - keys_b
        common = keys_a & keys_b
        
        # Moved = Map Change Only
        moved = {vid for vid in common if a[vid]["map"] != b[vid]["map"]}
        state_changed = {vid for vid in common if a[vid]["state"] != b[vid]["state"]}
        
        f_reg = self._vars["filter_region"].get()
        f_state = self._vars["filter_state"].get()
        
        all_keys = keys_a | keys_b
        sorted_keys = sorted(all_keys, key=lambda k: ((b.get(k) or a.get(k)).get("map") or "", k))
        
        displayed_count = 0
        for vid in sorted_keys:
            v = b.get(vid) or a.get(vid)
            if f_reg != "All Regions" and v.get("map") != f_reg: continue
            if f_state != "All States" and v.get("state") != f_state: continue
            
            tag = ""
            if vid in added: tag = "added"
            elif vid in removed: tag = "removed"
            elif vid in moved: tag = "moved"
            elif vid in state_changed: tag = "state_changed"
            
            disp_v = b.get(vid) or a.get(vid)
            display_id = vid.split("::")[0]
            
            self.tree.insert("", "end", values=(
                display_id, disp_v.get("map", "None"), disp_v.get("state", "unknown"),
                f"{disp_v.get('fuel')}" if disp_v.get('fuel') is not None else "--",
                f"{disp_v.get('damage')}" if disp_v.get('damage') is not None else "--"
            ), tags=(tag,))
            displayed_count += 1
            
        self.lbl_summary.config(text=f"Vehicles: {len(keys_b)} (B) | +Added: {len(added)} | -Removed: {len(removed)} | ↔ Moved: {len(moved)}")

    def on_folder_load(self, folder_path: str):
        if self._frame: 
            self._vars["external_path"].set("")
            self.refresh()

    def execute(self, context: Any) -> Dict[str, Any]:
        """
        Note: Logic identifies the most recently modified fog file to focus the reveal.
        """
        if not self._context or not self._context.save_folder:
            return {"success": False, "error": "No save folder loaded. Select a folder to begin."}
            
        try:
            self.refresh()
            count = len(self._last_data) if self._last_data else 0
            return {"success": True, "summary": f"Vehicle audit refreshed. {count} vehicles tracked across all discovered maps."}
        except Exception as e:
            return {"success": False, "error": str(e)}
