# [PH4-UI-003] Main Application Hub (SAFETY FIRST)
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import sys
import os
from typing import Any

# Structural Alignment
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "core_engineering")))

# Foundation Components
from core_engineering.logging import logger
from core_engineering.errors.exceptions import ValidationError, IntegrityError, TransactionError
from core_engineering.recovery.recovery_manager import RecoveryManager
from core_engineering.execution.safe_executor import SafeExecutor
from core_engineering.engine.fast_cache import cache

# Engineering Components
from maprunner.maprunner import MapRunner
from mapper.field_mapper import FieldMapper
from mapper.validators import FieldValidator
from engine.mutation_engine import MutationEngine
from engine.save_adapter import SaveAdapter
from engine.transaction_manager import SaveTransactionManager

# UI Panel Imports
from ui.panels.player_panel import PlayerPanel
from ui.panels.truck_panel import TruckPanel
from ui.panels.upgrade_panel import UpgradePanel

class SnowRunnerEditorUI:
    """
    Final Control Hub for Phase 4.3.
    REFINEMENTS:
    - [PH4-EXEC-002] Safe Execution via SafeExecutor.
    - [PH4-LOG-001] Mission Observability (logger).
    - [PH1-REC-001] Automatic Engine Restoration (recovery).
    """
    
    def __init__(self, root):
        self.root = root
        self.root.title("SnowRunner Save Editor v4.5.2 (Hardened)")
        self.root.geometry("900x650")
        
        # 1. Foundation Load
        self.mpr = MapRunner()
        self.validator = FieldValidator(self.mpr)
        self.engine = MutationEngine(self.mpr, self.validator)
        self.adapter = SaveAdapter()
        self.tx_mgr = SaveTransactionManager(self.adapter)
        self.mapper = FieldMapper(self.mpr)
        
        # [PH4-PERF-004] Resolution Cache
        from core_engineering.engine.fast_cache import cache
        self.cache = cache
        
        # 2. Safety Infrastructure [PH4-SEC-001]
        self.recovery = RecoveryManager(self.engine)
        self.executor = SafeExecutor(self.recovery)
        
        # Session Context
        self.current_file_path = None
        
        # 3. Control Layout
        self.toolbar = ttk.Frame(self.root)
        self.toolbar.pack(side="top", fill="x", padx=5, pady=5)
        
        ttk.Button(self.toolbar, text="Load Save", command=self.load_file).pack(side="left", padx=5)
        ttk.Button(self.toolbar, text="Save Changes", command=self.save_file).pack(side="left", padx=5)
        ttk.Button(self.toolbar, text="Open Logs", command=self.open_logs_folder).pack(side="left", padx=5)
        
        # [PH4-PROD-UI] Onboarding Guidance Label
        self.status_label = ttk.Label(self.toolbar, text="STATUS: No Save Loaded - Please Open a File", foreground="red")
        self.status_label.pack(side="right", padx=10)
        
        # 4. Main Interface
        # Tab Control with Lazy Policy [PH4-PERF-003]
        self.notebook = ttk.Notebook(self.root)
        self.notebook.pack(fill="both", expand=True)
        self.notebook.bind("<<NotebookTabChanged>>", self._on_tab_change)
        
        # 1. Player Tab
        self.player_frame = ttk.Frame(self.notebook)
        self.notebook.add(self.player_frame, text="Player Progression")
        self.player_panel = PlayerPanel(self.player_frame, self.mapper, self.validator, self.apply_change)
        
        # 2. Trucks Tab
        self.truck_frame = ttk.Frame(self.notebook)
        self.notebook.add(self.truck_frame, text="Warehouse Fleet")
        self.truck_panel = TruckPanel(self.truck_frame, self.mapper, self.validator, self.apply_change)
        
        # 3. Upgrades Tab
        self.upgrade_frame = ttk.Frame(self.notebook)
        self.notebook.add(self.upgrade_frame, text="Upgrade Discovery")
        self.upgrade_panel = UpgradePanel(self.upgrade_frame, self.mapper, self.validator, self.apply_change)

    def load_file(self):
        """[PH4-PROD-001] Professional Load Flow."""
        file_path = filedialog.askopenfilename(
            title="Select SnowRunner Save File",
            filetypes=[
                ("SnowRunner Save (*.cfg, *.dat)", "*.cfg;*.dat"),
                ("All Files", "*.*")
            ]
        )
        
        if not file_path:
            return

        self.current_file_path = file_path
        
        result = self.executor.execute(
            lambda: self.adapter.read(self.current_file_path),
            context={"action": "load_file", "path": self.current_file_path}
        )
        
        if result["status"] == "SUCCESS":
            # [PH4-SAFE-INV] Invalidate Cache on Load
            self.cache.invalidate_all()
            self.engine.set_state(result["result"])
            
            # Update Status [PH4-PROD-UI]
            self.status_label.config(text=f"STATUS: Loaded {os.path.basename(file_path)}", foreground="green")
            
            self.refresh_ui()
            messagebox.showinfo("Success", f"Save file loaded successfully:\n{os.path.basename(file_path)}")
        else:
            messagebox.showerror("Load Failed", result["message"])

    def save_file(self):
        """
        [PH4-EXEC-002] EXECUTE PROTECTED TRANSACTION.
        Guarantees: Logged -> Checkpointed -> Atomic -> Translated on fail.
        """
        if not self.current_file_path:
            messagebox.showwarning("Warning", "No active save file loaded.")
            return

        result = self.executor.execute(
            lambda: self.tx_mgr.execute(self.current_file_path, self.engine.state),
            context={"action": "save_file", "path": self.current_file_path}
        )
        
        if result["status"] == "SUCCESS":
            # Nested status check from TransactionManager result
            sub_res = result["result"]
            if sub_res["status"] == "COMMITTED":
                # [PH4-SAFE-INV] Post-Commit Sync
                cache.invalidate_all()
                messagebox.showinfo("Success", 
                    "Save Successful. Transaction committed safely.\n\n"
                    "NOTE: A backup (.bak) of your original file has been created in the same folder.")
            else:
                 messagebox.showerror("Save Unsafe", sub_res.get("reason", "Unexpected failure."))
        else:
            # [PH4-SAFE-INV] CRITICAL FAIL: Force-wipe cache to ensure recovery state is resolved fresh
            cache.invalidate_all()
            
            # [PH4-UI-ESC] Severity-Based Escalation
            severity = result.get("severity", "ERROR")
            if severity == "CRITICAL":
                messagebox.showerror("CRITICAL SYSTEM FAILURE", 
                    f"A critical error occurred while writing to disk!\n\nID: {result['request_id']}\n\nMessage: {result['message']}\n\nSystem state has been restored to prevent data loss.")
            else:
                messagebox.showwarning("Action Countered", result["message"])

    def apply_change(self, field_path: str, value: Any):
        """[PH4-PERF-001] Targeted Mutator Gate."""
        result = self.executor.execute(
            lambda: self.engine.apply_change(field_path, value),
            context={"field": field_path, "value": value},
            affected_path=field_path # Optimization Trigger
        )
        
        if result["status"] == "SUCCESS":
             # [PH4-SAFE-INV] Invalidate cache on mutation success
             cache.invalidate_all()
             # Mark UI as dirty and refresh active surface
             self.refresh_ui()
        else:
             # Translated User-Safe Feedback
             messagebox.showwarning("Action Countered", result["message"])

    def refresh_ui(self):
        """
        [PH4-PERF-003] Lazy Resolution Pipeline.
        Only resolves state for the currently visible control surface.
        """
        if not self.notebook.tabs():
             return

        current_tab_idx = self.notebook.index("current")
        tab_text = self.notebook.tab(current_tab_idx, "text")

        # Resolve state from absolute truth (Phase 2 interpreted model)
        # In a real 4.4, we would also optimize the Mapper to be lazy.
        resolved_data = self.mapper.resolve(self.engine.state, {"source": "ui_lazy"})

        if "Player" in tab_text:
             self.player_panel.render(resolved_data["player"])
             print("PERF: Lazy Render (Player Panel)")
        elif "Fleet" in tab_text:
             self.truck_panel.render(resolved_data["trucks"])
             print("PERF: Lazy Render (Truck Panel)")
        elif "Upgrade" in tab_text:
             self.upgrade_panel.render(resolved_data)
             print("PERF: Lazy Render (Upgrade Panel)")

    def _on_tab_change(self, event):
        """Defer rendering until the user actually interacts with the tab."""
        self.refresh_ui()

    def open_logs_folder(self):
        """[PH4-PROD-SUP] Supportability Shortcut."""
        from core_engineering.logging.logger import app_logger
        try:
             os.startfile(app_logger.log_dir)
        except Exception as e:
             messagebox.showwarning("Support", f"Could not open logs folder: {e}")

if __name__ == "__main__":
    app_root = tk.Tk()
    app = SnowRunnerEditorUI(app_root)
    app_root.mainloop()
