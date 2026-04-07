import tkinter as tk
from tkinter import ttk, messagebox
from typing import Dict, Any, List, Optional
from data.objective_database import get_objective_db
from .base import BasePlugin

class ObjectivesPlugin(BasePlugin):
    """
    v113.00 Objectives+ Plugin.
    Provides a permissioned interface for mission management with advanced filtering and batch actions.
    """
    
    def __init__(self):
        self._context = None
        self._frame = None
        self._db = get_objective_db()
        self._vars = {}
        self.tree = None
        self._checked_ids = set()

    @property
    def id(self) -> str:
        return "objectives"

    @property
    def display_name(self) -> str:
        return "🎯 Objectives+"

    @property
    def category(self) -> str:
        return "ADVANCED"

    @property
    def plugin_type(self) -> str:
        return "mutation"

    @property
    def description(self) -> str:
        return "Comprehensive mission management. Use checkboxes to select multiple tasks/contracts across regions for batch completion or acceptance."

    @property
    def primary_action_name(self) -> str:
        return "Sync Mission Catalog"

    @property
    def permissions(self) -> Dict[str, Any]:
        return {"read": True, "write": True, "complete": True, "sts": True}

    def register(self, context: Any):
        self._context = context

    def render(self, parent: tk.Frame):
        self._frame = ttk.Frame(parent, padding=10)
        self._frame.pack(fill="both", expand=True)
        self._frame.columnconfigure(0, weight=1)
        self._frame.rowconfigure(1, weight=1)

        # 1. Filters
        filter_frame = ttk.LabelFrame(self._frame, text=" Advanced Mission Filters ", padding=10)
        filter_frame.grid(row=0, column=0, sticky="ew")
        
        # Row 1: Region & Map
        f_row1 = ttk.Frame(filter_frame)
        f_row1.pack(fill="x", pady=2)
        
        ttk.Label(f_row1, text="Region:").pack(side="left")
        self._vars["region"] = tk.StringVar(value="All Regions")
        self.region_combo = ttk.Combobox(f_row1, textvariable=self._vars["region"], state="readonly", width=25)
        self.region_combo.pack(side="left", padx=(5, 15))
        self.region_combo.bind("<<ComboboxSelected>>", self._on_region_change)

        ttk.Label(f_row1, text="Map:").pack(side="left")
        self._vars["map"] = tk.StringVar(value="All Maps")
        self.map_combo = ttk.Combobox(f_row1, textvariable=self._vars["map"], state="readonly", width=25)
        self.map_combo.pack(side="left", padx=5)
        self.map_combo.bind("<<ComboboxSelected>>", lambda e: self.refresh())

        # Row 2: Type & Selection
        f_row2 = ttk.Frame(filter_frame)
        f_row2.pack(fill="x", pady=2)

        ttk.Label(f_row2, text="Type:").pack(side="left")
        self._vars["type"] = tk.StringVar(value="All Types")
        self.type_combo = ttk.Combobox(f_row2, textvariable=self._vars["type"], state="readonly", width=25)
        self.type_combo["values"] = ["All Types", "Contract", "Task", "Contest"]
        self.type_combo.pack(side="left", padx=(5, 15))
        self.type_combo.bind("<<ComboboxSelected>>", lambda e: self.refresh())

        ttk.Button(f_row2, text="☑ Select All Visible", command=self._on_select_all).pack(side="left", padx=5)
        ttk.Button(f_row2, text="☐ Deselect All", command=self._on_deselect_all).pack(side="left", padx=5)

        # 2. TreeView
        tree_frame = ttk.Frame(self._frame)
        tree_frame.grid(row=1, column=0, sticky="nsew", pady=10)
        
        # [v113.00] Checkbox column added as leader
        # [v113.10] Added friendly Map column for better context
        cols = ("sel", "name", "type", "rewards", "status", "map", "id")
        self.tree = ttk.Treeview(tree_frame, columns=cols, show="headings", selectmode="none")
        
        self.tree.heading("sel", text="✓")
        self.tree.heading("name", text="Game Name")
        self.tree.heading("type", text="Type")
        self.tree.heading("rewards", text="Rewards")
        self.tree.heading("status", text="Status")
        self.tree.heading("map", text="Map Name")
        self.tree.heading("id", text="Technical ID")
        
        self.tree.column("sel", width=40, anchor="center")
        self.tree.column("name", width=350)
        self.tree.column("type", width=100)
        self.tree.column("rewards", width=120)
        self.tree.column("status", width=100)
        self.tree.column("map", width=150)
        self.tree.column("id", width=150)
        
        self.tree.pack(side="left", fill="both", expand=True)
        
        self.tree.bind("<Button-1>", self._on_click)
        
        sb = ttk.Scrollbar(tree_frame, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=sb.set); sb.pack(side="right", fill="y")

        # 3. Actions
        act_frame = ttk.Frame(self._frame)
        act_frame.grid(row=2, column=0, sticky="ew")
        
        self.btn_complete = ttk.Button(act_frame, text="✅ Complete Selected", command=self._on_complete)
        self.btn_complete.pack(side="right", padx=5)
        
        self.btn_accept = ttk.Button(act_frame, text="📥 Accept Selected", command=self._on_accept)
        self.btn_accept.pack(side="right", padx=5)
        
        ttk.Button(act_frame, text="🔄 Refresh", command=self.refresh).pack(side="right", padx=5)
        
        self._vars["stats"] = tk.StringVar(value="0 items listed")
        ttk.Label(act_frame, textvariable=self._vars["stats"], font=("Segoe UI", 9, "bold")).pack(side="left")

        self.refresh()

    def _on_region_change(self, event=None):
        reg = self._vars["region"].get()
        if reg == "All Regions":
            self.map_combo['values'] = ["All Maps"]
            self._vars["map"].set("All Maps")
        else:
            # [v113.10] Use Friendly Name Mapping for the Dropdown
            # IntegrityManager's map_labels has mid -> {region, name}
            map_ids = sorted(list(set(r['map_name'] for r in self._db.raw_list if r.get('region_name') == reg and r.get('map_name'))))
            
            # Map IDs back to Friendly Names for the UI
            friendly_maps = []
            labels = getattr(self._context, "map_labels", {})
            for mid in map_ids:
                if mid in labels:
                    friendly_maps.append(labels[mid]["name"])
                else:
                    friendly_maps.append(mid)
            
            self.map_combo['values'] = ["All Maps"] + sorted(friendly_maps)
            self._vars["map"].set("All Maps")
        self.refresh()

    def _on_click(self, event):
        item = self.tree.identify_row(event.y)
        column = self.tree.identify_column(event.x)
        if not item: return
        
        # Toggle if clicked on checkbox column
        if column == "#1":
            iid = item # ID is stored as the iid
            if iid in self._checked_ids:
                self._checked_ids.remove(iid)
                self.tree.set(item, "sel", "☐")
            else:
                self._checked_ids.add(iid)
                self.tree.set(item, "sel", "☑")

    def _on_select_all(self):
        for item in self.tree.get_children():
            self._checked_ids.add(item)
            self.tree.set(item, "sel", "☑")

    def _on_deselect_all(self):
        for item in self.tree.get_children():
            if item in self._checked_ids:
                self._checked_ids.remove(item)
            self.tree.set(item, "sel", "☐")

    def refresh(self):
        if not self._context or not self._frame: return
        
        def _perform_load():
            if not self._db.load_local():
                self._vars["stats"].set("⏳ Downloading mission catalog...")
                if self._db.refresh_from_web():
                    self._db.load_local()
                else:
                    self._vars["stats"].set("❌ Failed to load mission catalog.")
                    return False
            return True

        if not self._db.raw_list:
            import threading
            self._vars["stats"].set("⏳ Initializing mission catalog...")
            def bg_load():
                if _perform_load():
                    if self._frame and self._frame.winfo_exists():
                        self._frame.after(0, self._populate_tree)
            
            threading.Thread(target=bg_load, daemon=True).start()
            return
        
        self._populate_tree()

    def _populate_tree(self):
        if not self._db.raw_list: return

        # Sync Region values if empty
        if not self.region_combo['values'] or self.region_combo['values'] == ("All Regions",):
            regions = sorted(list(set(r['region_name'] for r in self._db.raw_list if r.get('region_name'))))
            self.region_combo['values'] = ["All Regions"] + regions

        # [v113.10] BATCH RENDERING OVERHAUL
        # Prevents "Not Responding" hangs by inserting items in chunks.
        self.tree.delete(*self.tree.get_children())
        self._vars["stats"].set("⏳ Refreshing mission catalog...")
        
        filtered_items = []
        for item in self._db.raw_list:
            if sel_reg != "All Regions" and item.get("region_name") != sel_reg: continue
            
            # [v113.10] Map-to-ID matching for friendly dropdown
            mid = item.get("map_name")
            labels = getattr(self._context, "map_labels", {})
            current_friendly = labels.get(mid, {}).get("name", mid) if mid else "Unknown"
            
            if sel_map != "All Maps" and current_friendly != sel_map: continue
            
            otype = item.get("type", "Unknown")
            if sel_type != "All Types":
                # Case-Insensitive Normalized Comparison
                if sel_type.upper() != otype.upper(): continue
            
            filtered_items.append((item, current_friendly))

        # Start Batch Insertion
        self._batch_insert(filtered_items, 0)

    def _batch_insert(self, items: List[Any], start_idx: int):
        """Worker to insert items in small chunks to keep UI responsive."""
        if not self.tree or not self.tree.winfo_exists(): return
        
        chunk_size = 50
        end_idx = min(start_idx + chunk_size, len(items))
        
        analytics = self._context.get_progression_data(self)
        finished_ids = set(analytics.get("unknown_in_save", []))
        accepted_ids = set(analytics.get("activated_objectives", []))
        
        for i in range(start_idx, end_idx):
            item, current_friendly = items[i]
            iid = item.get("key")
            name = item.get("displayName", iid)
            otype = item.get("type", "Unknown")
            status = "Completed" if iid in finished_ids else ("Accepted" if iid in accepted_ids else "Available")
            
            money = item.get("money", 0)
            xp = item.get("experience", 0)
            rewards = f"${money} / {xp} XP" if (money or xp) else "None"
            
            chk = "☑" if iid in self._checked_ids else "☐"
            self.tree.insert("", "end", iid, values=(chk, name, otype, rewards, status, current_friendly, iid))

        if end_idx < len(items):
            # Continue next batch
            self._frame.after(5, lambda: self._batch_insert(items, end_idx))
        else:
            # Done
            self._vars["stats"].set(f"✅ {len(items)} missions synchronized")

    def _on_complete(self):
        if not self._checked_ids:
            messagebox.showinfo("Selection", "Please select missions using the checkboxes first.")
            return
        
        count = len(self._checked_ids)
        if messagebox.askyesno("Confirm Batch", f"Complete {count} selected missions?\n\nThis will apply rewards and sync world markers."):
            try:
                res = self._context.execute_feature("objective_complete", {"objective_ids": list(self._checked_ids), "status": "COMPLETED"}, self)
                if res.get("success"):
                    messagebox.showinfo("Success", f"{count} objectives completed successfully.")
                    self._checked_ids.clear()
                    self.refresh()
                else:
                    messagebox.showerror("Error", res.get("error"))
            except Exception as e:
                messagebox.showerror("Plugin Error", str(e))

    def _on_accept(self):
        if not self._checked_ids:
            messagebox.showinfo("Selection", "Please select missions to accept using the checkboxes.")
            return
        
        count = len(self._checked_ids)
        if messagebox.askyesno("Confirm Accept", f"Add {count} selected missions to your 'Active Tasks' in-game?\n\nYou can then complete them manually."):
            try:
                for oid in list(self._checked_ids):
                     self._context.execute_feature("accept_objective", {"objective_id": oid}, self)
                
                messagebox.showinfo("Success", f"{count} objectives accepted. Reload your save in-game to see them in 'Active Tasks'.")
                self._checked_ids.clear()
                self.refresh()
            except Exception as e:
                messagebox.showerror("Plugin Error", str(e))

    def on_folder_load(self, folder_path: str):
        self._checked_ids.clear()
        self.refresh()

    def execute(self, context: Any) -> Dict[str, Any]:
        try:
            self.refresh()
            return {"success": True, "summary": "Mission catalog and completion status synchronized."}
        except Exception as e:
            return {"success": False, "error": str(e)}
