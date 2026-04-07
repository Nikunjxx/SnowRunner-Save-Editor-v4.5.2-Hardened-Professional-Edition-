import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox
from typing import Dict, Any, List, Optional
from .base import BasePlugin

class PluginManagerPlugin(BasePlugin):
    """
    v111.00 System-level Plugin Manager UI.
    Provides centralized discovery, metadata introspection, and transactional execution.
    """
    
    def __init__(self, manager_ref):
        self._manager = manager_ref # PluginManager instance
        self._context = None
        self._frame = None
        self._selected_plugin_id = None
        
        self._vars = {
            "name": None,
            "desc": None,
            "type": None,
            "action": None,
            "status_summary": None,
            "progress": None
        }

    @property
    def id(self) -> str:
        return "system_plugin_manager"

    @property
    def display_name(self) -> str:
        return "🛠️ Plugin Manager"

    @property
    def category(self) -> str:
        return "SYSTEM"

    @property
    def plugin_type(self) -> str:
        return "read"

    @property
    def description(self) -> str:
        return "Centralized control panel for all installed features. Audit capabilities, view metadata, and execute primary actions."

    @property
    def primary_action_name(self) -> str:
        return "Refresh Plugin List"

    def register(self, context: Any):
        self._context = context
        self._vars["name"] = tk.StringVar(value="Select a Plugin")
        self._vars["desc"] = tk.StringVar(value="Details will appear here.")
        self._vars["type"] = tk.StringVar(value="--")
        self._vars["action"] = tk.StringVar(value="Run Action")
        self._vars["status_summary"] = tk.StringVar(value="Ready.")
        self._vars["progress"] = tk.DoubleVar(value=0.0)

    def render(self, parent: tk.Frame):
        self._frame = ttk.Frame(parent, padding=10)
        self._frame.pack(fill="both", expand=True)
        
        # Main Paned Window
        paned = ttk.PanedWindow(self._frame, orient="horizontal")
        paned.pack(fill="both", expand=True)
        
        # --- LEFT: Discovery List ---
        left_frame = ttk.Frame(paned, padding=5)
        paned.add(left_frame, weight=1)
        
        ttk.Label(left_frame, text="Discovered Features", font=("Segoe UI", 10, "bold")).pack(anchor="w", pady=(0, 5))
        
        cols = ("name", "category")
        self.tree = ttk.Treeview(left_frame, columns=cols, show="headings", selectmode="browse")
        self.tree.heading("name", text="Feature")
        self.tree.heading("category", text="Category")
        self.tree.column("category", width=100)
        self.tree.pack(fill="both", expand=True)
        self.tree.bind("<<TreeviewSelect>>", self._on_plugin_selected)
        
        # --- RIGHT: Metadata & Control ---
        right_frame = ttk.Frame(paned, padding=10)
        paned.add(right_frame, weight=2)
        
        # Metadata Header
        meta_header = ttk.LabelFrame(right_frame, text=" Feature Details ", padding=15)
        meta_header.pack(fill="x", pady=(0, 10))
        
        ttk.Label(meta_header, textvariable=self._vars["name"], font=("Segoe UI", 14, "bold")).pack(anchor="w")
        ttk.Label(meta_header, textvariable=self._vars["type"], font=("Segoe UI", 9, "italic"), foreground="#7f8c8d").pack(anchor="w")
        
        tk.Label(meta_header, textvariable=self._vars["desc"], wraplength=450, justify="left", font=("Segoe UI", 10), pady=10).pack(anchor="w")
        
        # Action Control
        ctrl_frame = ttk.Frame(right_frame)
        ctrl_frame.pack(fill="x", pady=10)
        
        self.btn_run = ttk.Button(ctrl_frame, textvariable=self._vars["action"], style="Accent.TButton", 
                                 command=self._on_run_plugin, state="disabled")
        self.btn_run.pack(side="left", padx=5)
        
        # --- BOTTOM: Layered Output Panel ---
        output_frame = ttk.LabelFrame(right_frame, text=" Execution Status ", padding=10)
        output_frame.pack(fill="both", expand=True)
        
        # Summary Row
        summary_row = ttk.Frame(output_frame)
        summary_row.pack(fill="x", pady=(0, 5))
        ttk.Label(summary_row, textvariable=self._vars["status_summary"], font=("Segoe UI", 9, "bold")).pack(side="left")
        
        # Progress Bar
        self.progress_bar = ttk.Progressbar(output_frame, variable=self._vars["progress"], mode="determinate")
        self.progress_bar.pack(fill="x", pady=5)
        
        # Technical Logs (Expandable)
        ttk.Label(output_frame, text="Technical Logs:", font=("Segoe UI", 8)).pack(anchor="w")
        self.log_text = scrolledtext.ScrolledText(output_frame, height=8, font=("Consolas", 9), state="disabled", bg="#1e1e1e", fg="#d4d4d4")
        self.log_text.pack(fill="both", expand=True)

        self.refresh()

    def refresh(self):
        if not self.tree: return
        self.tree.delete(*self.tree.get_children())
        
        plugins = self._manager.get_all_plugins()
        for p in plugins:
            if p.id == self.id: continue # Don't list itself
            self.tree.insert("", "end", iid=p.id, values=(p.display_name, p.category))
        
        self._vars["status_summary"].set(f"Feature catalog updated: {len(plugins)-1} plugins found.")

    def _on_plugin_selected(self, event):
        sel = self.tree.selection()
        if not sel: return
        
        p_id = sel[0]
        self._selected_plugin_id = p_id
        plugin = self._manager.get_plugin(p_id)
        if not plugin: return
        
        caps = plugin.capabilities
        self._vars["name"].set(plugin.display_name)
        self._vars["type"].set(f"Type: {caps['type'].upper()} | ID: {p_id}")
        self._vars["desc"].set(caps['description'])
        self._vars["action"].set(f"Execute: {caps['primary_action']}")
        
        # Visual cue for mutations
        if caps['type'] == "mutation":
            self.btn_run.configure(style="Warning.TButton") # Needs Warning style defined in root
        else:
            self.btn_run.configure(style="Accent.TButton")
            
        self.btn_run.configure(state="normal")

    def _on_run_plugin(self):
        if not self._selected_plugin_id: return
        
        plugin = self._manager.get_plugin(self._selected_plugin_id)
        if not plugin: return
        
        # Zero-Trust Confirmation for Mutations
        if plugin.plugin_type == "mutation":
            if not messagebox.askyesno("Confirm Action", 
                                     f"Are you sure you want to execute '{plugin.primary_action_name}'?\n\n"
                                     "This will modify your save files. A transaction-safe backup will be created automatically."):
                return

        # UI Setup for execution
        self._vars["status_summary"].set(f"Executing {plugin.id}...")
        self._vars["progress"].set(20.0)
        self.btn_run.configure(state="disabled")
        self._log(f">>> START: {plugin.id}", clear=True)
        self._frame.update_idletasks()
        
        # Execution
        try:
            # Atomic run via PluginManager (handles transaction externally)
            result = self._manager.run_plugin(self._selected_plugin_id)
            
            self._vars["progress"].set(100.0)
            if result.get("success"):
                self._vars["status_summary"].set("Success")
                self._log(f"SUCCESS: {result.get('summary', 'Action completed.')}")
                if "tx_id" in result: self._log(f"TX_ID: {result['tx_id']}")
                messagebox.showinfo("Success", result.get('summary', "Action completed successfully."))
            else:
                self._vars["status_summary"].set("Failed")
                self._log(f"ERROR: {result.get('error', 'Unknown failure')}")
                messagebox.showerror("Execution Failed", result.get('error', "Unknown error occurred."))
                
        except Exception as e:
            self._vars["status_summary"].set("Critical Failure")
            self._log(f"CRITICAL: {str(e)}")
            messagebox.showerror("Critical Error", str(e))
        finally:
            self.btn_run.configure(state="normal")
            self.refresh()

    def _log(self, text: str, clear: bool = False):
        self.log_text.configure(state="normal")
        if clear: self.log_text.delete(1.0, tk.END)
        self.log_text.insert(tk.END, text + "\n")
        self.log_text.see(tk.END)
        self.log_text.configure(state="disabled")

    def execute(self, context: Any) -> Dict[str, Any]:
        self.refresh()
        return {"success": True, "summary": "Plugin catalog refreshed."}
