import tkinter as tk
from tkinter import ttk, messagebox
import time
import os
from typing import Dict, Any, List, Optional
from .base import BasePlugin

class MapUnlockPlugin(BasePlugin):
    """
    v110.60 Map Unlock & Exploration Plugin.
    Provides transaction-aware fog reveal operations for traversed maps.
    """
    
    def __init__(self):
        self._context = None
        self._frame = None
        self._vars = {}
        self._buttons = {}

    @property
    def id(self) -> str:
        return "map_unlock"

    @property
    def display_name(self) -> str:
        return "🌍 Map Unlock"

    @property
    def category(self) -> str:
        return "ADVANCED"

    @property
    def plugin_type(self) -> str:
        return "mutation"

    @property
    def description(self) -> str:
        return "[v111.00] Non-invasive fog reveal for traversable maps. This removes the 'Fog of War' from your map view without affecting mission progression, discoveries, or game stats."

    @property
    def primary_action_name(self) -> str:
        return "Reveal Map Fog"

    @property
    def permissions(self) -> Dict[str, Any]:
        return {"read": True, "write": True, "fog": True}

    def register(self, context: Any):
        self._context = context

    def render(self, parent: tk.Frame):
        self._frame = ttk.Frame(parent, padding=10)
        self._frame.pack(fill="both", expand=True)
        self._frame.columnconfigure(0, weight=1)
        
        # --- 1. Header ---
        header_frame = ttk.Frame(self._frame, padding=(10, 5))
        header_frame.grid(row=0, column=0, sticky="ew")
        ttk.Label(header_frame, text="🌍 Map Exploration & Fog Reveal", font=("Segoe UI", 14, "bold")).pack(side="left")
        
        self._vars["status"] = tk.StringVar(value="Idle")
        ttk.Label(header_frame, textvariable=self._vars["status"], font=("Segoe UI", 9, "italic"), foreground="#7f8c8d").pack(side="right")

        # --- 2. Stats ---
        audit_frame = ttk.LabelFrame(self._frame, text=" Discovery Statistics ", padding=15)
        audit_frame.grid(row=1, column=0, sticky="ew", padx=10, pady=10)
        
        self._create_stat(audit_frame, "Total Maps", "total_maps", 0)
        self._create_stat(audit_frame, "Visited (Available)", "visited", 1, "#3498db")
        self._create_stat(audit_frame, "Unexplored (Skipped)", "skipped", 2, "#e67e22")

        # --- 3. Controls ---
        ctrl_frame = ttk.LabelFrame(self._frame, text=" Batch Reveal Controls ", padding=15)
        ctrl_frame.grid(row=2, column=0, sticky="nsew", padx=10, pady=10)
        ctrl_frame.columnconfigure(0, weight=1)
        ctrl_frame.columnconfigure(1, weight=1)
        ctrl_frame.columnconfigure(2, weight=1)

        # 3.1 Current
        c_f = ttk.Frame(ctrl_frame, padding=5)
        c_f.grid(row=0, column=0, sticky="nsew")
        ttk.Label(c_f, text="Current Focus", font=("Segoe UI", 9, "bold")).pack()
        self._buttons["current"] = ttk.Button(c_f, text="Reveal Active Map", command=self._reveal_current)
        self._buttons["current"].pack(fill="x", pady=10)

        # 3.2 Region
        r_f = ttk.Frame(ctrl_frame, padding=5)
        r_f.grid(row=0, column=1, sticky="nsew")
        ttk.Label(r_f, text="Regional Batch", font=("Segoe UI", 9, "bold")).pack()
        self._vars["region_sel"] = tk.StringVar()
        self.region_combo = ttk.Combobox(r_f, textvariable=self._vars["region_sel"], state="readonly")
        self.region_combo.pack(fill="x", pady=(5, 0))
        self._buttons["region"] = ttk.Button(r_f, text="Reveal Region", command=self._reveal_region)
        self._buttons["region"].pack(fill="x", pady=5)

        # 3.3 Global
        g_f = ttk.Frame(ctrl_frame, padding=5)
        g_f.grid(row=0, column=2, sticky="nsew")
        ttk.Label(g_f, text="Global Operations", font=("Segoe UI", 9, "bold")).pack()
        self._buttons["global"] = ttk.Button(g_f, text="Reveal All Visited", command=self._reveal_global)
        self._buttons["global"].pack(fill="x", pady=10)

        # --- 4. Info ---
        footer = ttk.Frame(self._frame, padding=10)
        footer.grid(row=3, column=0, sticky="ew")
        ttk.Label(footer, text="🛡️ Non-invasive: Only affects visited maps. Rollback supported.", font=("Segoe UI", 8), foreground="#95a5a6").pack()

        self.refresh()

    def _create_stat(self, parent, label, var_id, col, color=None):
        f = ttk.Frame(parent)
        f.grid(row=0, column=col, sticky="ew")
        parent.columnconfigure(col, weight=1)
        ttk.Label(f, text=label, font=("Segoe UI", 8)).pack()
        v = tk.StringVar(value="--")
        self._vars[var_id] = v
        l = ttk.Label(f, textvariable=v, font=("Segoe UI", 12, "bold"))
        if color: l.configure(foreground=color)
        l.pack()

    def refresh(self):
        if not self._context or not self._frame: return
        
        # Check permissions
        if "read" not in getattr(self, "permissions", {}): return
        
        sc = self._context.get_save_registry()
        reg_ctx = self._context.get_region_metadata()
        fog_ctx = sc.get("fog", {})
        
        total = 0
        visited = 0
        for lvls in reg_ctx.values():
            total += len(lvls)
            for l in lvls:
                if l.lower() in fog_ctx: visited += 1
        
        self._vars["total_maps"].set(str(total))
        self._vars["visited"].set(str(visited))
        self._vars["skipped"].set(str(total - visited))
        
        # Regions
        regions = sorted(list(reg_ctx.keys()))
        self.region_combo['values'] = regions
        if not self._vars["region_sel"].get() and regions:
            self._vars["region_sel"].set(regions[0])
            
        self._enable_all()
        self._vars["status"].set("Exploration metadata synchronized.")

    def _disable_all(self):
        for btn in self._buttons.values(): btn.configure(state="disabled")

    def _enable_all(self):
        for btn in self._buttons.values(): btn.configure(state="normal")

    def _run_batch(self, scope, **kwargs):
        self._vars["status"].set(f"Executing {scope} reveal...")
        self._frame.update_idletasks()
        
        try:
            res = self._context.execute_feature("map_unlock", {"scope": scope, **kwargs}, self)
            if res.get("success"):
                revealed = len(res.get("files_written", []))
                clear = len(res.get("already_clear", []))
                msg = f"Reveal Complete!\n\n✅ Newly Revealed: {revealed}\n⚠ Already Clear: {clear}"
                messagebox.showinfo("Success", msg)
            else:
                messagebox.showerror("Error", f"Failed: {res.get('error')}")
        except Exception as e:
            messagebox.showerror("Plugin Error", str(e))
        finally:
            self.refresh()

    def _reveal_current(self):
        sc = self._context.get_save_registry()
        target = self._context.save_folder
        fog_ctx = sc.get("fog", {})
        
        latest_id = None
        latest_time = 0
        for lid, fname in fog_ctx.items():
            fpath = os.path.join(target, fname)
            if os.path.exists(fpath):
                mtime = os.path.getmtime(fpath)
                if mtime > latest_time:
                    latest_time = mtime; latest_id = lid
                    
        if not latest_id:
            messagebox.showwarning("Warning", "Could not detect active level.")
            return
            
        if messagebox.askyesno("Confirm", f"Reveal fog for {latest_id}?"):
            self._run_batch("current", level_id=latest_id)

    def _reveal_region(self):
        reg = self._vars["region_sel"].get()
        if reg and messagebox.askyesno("Confirm", f"Reveal all visited maps in {reg}?"):
            self._run_batch("region", region_name=reg)

    def _reveal_global(self):
        if messagebox.askyesno("Global Reveal", "Process ALL visited maps across all regions?"):
            self._run_batch("global")

    def on_folder_load(self, folder_path: str):
        self.refresh()

    def execute(self, context: Any) -> Dict[str, Any]:
        """
        Primary action: Reveal fog for the most recently active map.
        Note: Logic identifies the most recently modified fog file to focus the reveal.
        """
        if not self._context or not self._context.save_folder:
            return {"success": False, "error": "No save folder loaded."}

        if not messagebox.askyesno("Confirm Map Unlock", "Reveal fog for the most recently active map?\n\nThis mutation is safe and only affects the fog of war."):
            return {"success": False, "error": "Action cancelled by user."}

        # 1. Identify target map
        sc = self._context.get_save_registry()
        target = self._context.save_folder
        fog_ctx = sc.get("fog", {})
        
        latest_id = None
        latest_time = 0
        for lid, fname in fog_ctx.items():
            fpath = os.path.join(target, fname)
            if os.path.exists(fpath):
                mtime = os.path.getmtime(fpath)
                if mtime > latest_time:
                    latest_time = mtime; latest_id = lid
                    
        if not latest_id:
            return {"success": False, "error": "Could not detect active level from fog metadata."}

        # 2. Execute via context
        try:
            res = self._context.execute_feature("map_unlock", {"scope": "current", "level_id": latest_id}, self)
            if res.get("success"):
                revealed = len(res.get("files_written", []))
                return {"success": True, "summary": f"Revealed fog for {latest_id}. {revealed} files updated."}
            else:
                return {"success": False, "error": res.get("error", "Unknown reveal error")}
        except Exception as e:
            return {"success": False, "error": str(e)}
        finally:
            self.refresh()
