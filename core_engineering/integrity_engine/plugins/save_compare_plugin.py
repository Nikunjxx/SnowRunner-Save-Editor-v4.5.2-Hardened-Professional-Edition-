import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from typing import Dict, Any, List, Optional
from .base import BasePlugin

class SaveComparePlugin(BasePlugin):
    """
    v110.70 Save Comparison Plugin.
    Provides a high-fidelity, read-only diff between the active save 
    and an external save folder.
    """
    
    def __init__(self):
        self._context = None
        self._frame = None
        self._vars = {
            "external_path": None,
            "summary": None,
            "diff_data": None
        }

    @property
    def id(self) -> str:
        return "save_compare"

    @property
    def display_name(self) -> str:
        return "🔍 Save Compare"

    @property
    def category(self) -> str:
        return "INTELLIGENCE"

    @property
    def plugin_type(self) -> str:
        return "read"

    @property
    def description(self) -> str:
        return "Advanced delta analysis between two save folders. Compares economy, discovered maps, fleet status, and mission completion."

    @property
    def primary_action_name(self) -> str:
        return "Compare Saves"

    @property
    def permissions(self) -> Dict[str, Any]:
        return {"read": True, "write": False}

    def register(self, context: Any):
        self._context = context
        self._vars["external_path"] = tk.StringVar(value="")
        self._vars["summary"] = tk.StringVar(value="Select an external save folder to begin comparison.")

    def render(self, parent: tk.Frame):
        self._frame = ttk.Frame(parent, padding=15)
        self._frame.pack(fill="both", expand=True)
        
        # 1. Selection Header
        header = ttk.LabelFrame(self._frame, text=" Target Save (B) ", padding=10)
        header.pack(fill="x", pady=(0, 10))
        
        ttk.Label(header, text="Folder:").pack(side="left")
        ttk.Entry(header, textvariable=self._vars["external_path"], width=60).pack(side="left", padx=5)
        ttk.Button(header, text="Browse...", command=self._on_browse).pack(side="left")
        ttk.Button(header, text="Compare Now", command=self.refresh).pack(side="right")

        # 2. Main Layout (Scrollable)
        container = ttk.Frame(self._frame)
        container.pack(fill="both", expand=True)
        container.columnconfigure(0, weight=1)
        container.columnconfigure(1, weight=1)

        # Left Column: Summary, Economy, Maps, Vehicles
        left_col = ttk.Frame(container)
        left_col.grid(row=0, column=0, sticky="nsew", padx=(0, 5))
        
        econ_frame = ttk.LabelFrame(left_col, text=" 📊 Economy Delta ", padding=10)
        econ_frame.pack(fill="x")
        
        self.lbl_xp = ttk.Label(econ_frame, text="XP Delta: --", font=("Segoe UI", 11))
        self.lbl_xp.pack(anchor="w")
        self.lbl_money = ttk.Label(econ_frame, text="Money Delta: --", font=("Segoe UI", 11, "bold"))
        self.lbl_money.pack(anchor="w")

        map_frame = ttk.LabelFrame(left_col, text=" 🗺️ Map Discovery ", padding=10)
        map_frame.pack(fill="x", pady=10)
        self.lbl_maps = ttk.Label(map_frame, text="New Regions Visited: --")
        self.lbl_maps.pack(anchor="w")

        veh_frame = ttk.LabelFrame(left_col, text=" 🚚 Vehicle Discovery ", padding=10)
        veh_frame.pack(fill="x")
        self.lbl_veh = ttk.Label(veh_frame, text="Fleet Delta: --")
        self.lbl_veh.pack(anchor="w")

        # Right Column: Objectives
        right_col = ttk.Frame(container)
        right_col.grid(row=0, column=1, sticky="nsew", padx=(5, 0))
        
        obj_frame = ttk.LabelFrame(right_col, text=" 🎯 Missions Delta ", padding=10)
        obj_frame.pack(fill="both", expand=True)
        
        self.tree_obj = ttk.Treeview(obj_frame, columns=("type", "id"), show="headings", height=12)
        self.tree_obj.heading("type", text="Status")
        self.tree_obj.heading("id", text="Objective ID")
        self.tree_obj.column("type", width=70)
        self.tree_obj.pack(fill="both", expand=True)
        
        sb = ttk.Scrollbar(obj_frame, orient="vertical", command=self.tree_obj.yview)
        self.tree_obj.configure(yscrollcommand=sb.set); sb.pack(side="right", fill="y")

        # 3. Footer: Metadata Health
        footer = ttk.LabelFrame(self._frame, text=" ⚠️ Metadata Health ", padding=10)
        footer.pack(fill="x", pady=(10, 0))
        self.lbl_meta = ttk.Label(footer, text="Unknown IDs Check: --", foreground="orange")
        self.lbl_meta.pack(anchor="w")

    def _on_browse(self):
        path = filedialog.askdirectory(title="Select External Save Folder (B)")
        if path:
            self._vars["external_path"].set(path)
            self.refresh()

    def refresh(self):
        if not self._context or not self._frame: return
        ext_path = self._vars["external_path"].get()
        if not ext_path: return

        # Identity Short-circuit
        if ext_path == self._context.save_folder:
            self._reset_ui("Folders are identical. Delta is zero.")
            return

        try:
            # 1. Fetch Ephemeral Snapshots
            snap_a = self._context.get_active_snapshot(self)
            
            # 2. Peek External Save (B)
            res_b = self._context.peek_external_save(ext_path, self)
            if "error" in res_b:
                 self._reset_ui(res_b["error"])
                 return
            
            # 3. Build Diff
            self._build_diff(snap_a, res_b)
            
        except Exception as e:
            self._reset_ui(f"Comparison Error: {str(e)}")

    def _build_diff(self, a, b):
        """Implements the set-based diff builder logic."""
        # Economy
        delta_xp = b["economy"]["xp"] - a["economy"]["xp"]
        delta_money = b["economy"]["money"] - a["economy"]["money"]
        
        self.lbl_xp.config(text=f"XP Delta: {self._fmt_num(delta_xp)}", foreground="green" if delta_xp >= 0 else "red")
        self.lbl_money.config(text=f"Money Delta: {self._fmt_num(delta_money)}", foreground="green" if delta_money >= 0 else "red")

        # Maps
        added_maps = b["maps"]["visited"] - a["maps"]["visited"]
        removed_maps = a["maps"]["visited"] - b["maps"]["visited"]
        self.lbl_maps.config(text=f"New Maps Visited: +{len(added_maps)} / -{len(removed_maps)}")

        # Vehicles (v110.90)
        veh_a = a.get("vehicles", {})
        veh_b = b.get("vehicles", {})
        keys_a = set(veh_a.keys())
        keys_b = set(veh_b.keys())
        added_v = keys_b - keys_a
        removed_v = keys_a - keys_b
        moved_v = {vid for vid in (keys_a & keys_b) if veh_a[vid]["map"] != veh_b[vid]["map"]}
        
        self.lbl_veh.config(text=f"Fleet Delta: +{len(added_v)} Added / -{len(removed_v)} Removed / ↔ {len(moved_v)} Moved")

        # Objectives
        added_obj = b["objectives"]["completed"] - a["objectives"]["completed"]
        removed_obj = a["objectives"]["completed"] - b["objectives"]["completed"]
        
        self.tree_obj.delete(*self.tree_obj.get_children())
        for oid in sorted(list(added_obj)):
            self.tree_obj.insert("", "end", values=("ADDED", oid), tags=('added',))
        for oid in sorted(list(removed_obj)):
            self.tree_obj.insert("", "end", values=("REMOVED", oid), tags=('removed',))
            
        self.tree_obj.tag_configure('added', foreground='green')
        self.tree_obj.tag_configure('removed', foreground='red')

        # Metadata
        unknown_b = b["metadata"]["unknown_ids"]
        self.lbl_meta.config(text=f"External Save contains {len(unknown_b)} Objective IDs not found in Metadata.")

    def _fmt_num(self, val):
        sign = "+" if val > 0 else ""
        return f"{sign}{val:,}"

    def _reset_ui(self, message):
        self.lbl_xp.config(text="XP Delta: --", foreground="black")
        self.lbl_money.config(text="Money Delta: --", foreground="black")
        self.lbl_maps.config(text="New Regions Visited: --")
        self.lbl_veh.config(text="Fleet Delta: --")
        self.tree_obj.delete(*self.tree_obj.get_children())
        self.lbl_meta.config(text=message)

    def on_folder_load(self, folder_path: str):
        # We don't auto-compare on load, but we reset UI status
        if self._frame: self._reset_ui("Select external folder to compare.")

    def execute(self, context: Any) -> Dict[str, Any]:
        """Primary action: Execute the comparison logic."""
        ext_path = self._vars["external_path"].get()
        if not ext_path:
            return {"success": False, "error": "No external save folder selected for comparison (Target B)."}
        
        try:
            self.refresh()
            return {"success": True, "summary": f"Comparison with {os.path.basename(ext_path)} completed."}
        except Exception as e:
            return {"success": False, "error": str(e)}
