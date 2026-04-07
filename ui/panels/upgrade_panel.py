# [PH3-UI-012] Upgrade Management Panel (ADVANCED)
import tkinter as tk
from tkinter import ttk, messagebox

class UpgradePanel:
    """
    Control Layer for Vehicle Upgrades.
    REFINEMENTS:
    - Context-Aware Filtering (via MapRunner).
    - Identity-Based Selection (Truck ID + Upgrade ID).
    - Atomic safe-edit pipeline.
    """
    
    def __init__(self, parent, mapper, validator, on_apply_callback):
        self.parent = parent
        self.mapper = mapper
        self.validator = validator
        self.on_apply_callback = on_apply_callback
        
        # State Context (Rule: Local only for UI state)
        self.active_truck_id = None
        self.truck_ids = []
        
        self._setup_view()

    def _setup_view(self):
        """Builds static layout with filtered discovery view."""
        frame = ttk.LabelFrame(self.parent, text="Part Catalog (Knowledge Filtered)", padding=10)
        frame.pack(fill="both", expand=True, padx=10, pady=10)
        
        # 1. Truck Selector (From Resolved Warehouse)
        select_frame = ttk.Frame(frame)
        select_frame.pack(fill="x", pady=5)
        
        ttk.Label(select_frame, text="Active Vehicle:").pack(side=tk.LEFT)
        self.truck_selector = ttk.Combobox(select_frame, state="readonly")
        self.truck_selector.pack(side=tk.LEFT, fill="x", expand=True, padx=5)
        self.truck_selector.bind("<<ComboboxSelected>>", self._on_truck_change)
        
        # 2. Upgrade Treeview
        self.tree = ttk.Treeview(frame, columns=("ID", "Name", "Map", "Class"), show="headings")
        self.tree.heading("ID", text="Part ID")
        self.tree.heading("Name", text="Part Name")
        self.tree.heading("Map", text="Map Location")
        self.tree.heading("Class", text="Slot Class")
        
        self.tree.column("ID", width=150)
        self.tree.column("Name", width=200)
        self.tree.column("Map", width=150)
        
        self.tree.pack(side="left", fill="both", expand=True, pady=10)
        
        self.scrollbar = ttk.Scrollbar(frame, orient=tk.VERTICAL, command=self.tree.yview)
        self.tree.configure(yscroll=self.scrollbar.set)
        self.scrollbar.pack(side="right", fill="y", pady=10)
        
        self.tree.bind("<Double-1>", self._on_part_double_click)

    def render(self, resolved_ui_state: dict):
        """
        Populates truck list and refreshes filtered view.
        UI receives full resolved state to understand cross-mappings.
        """
        trucks = resolved_ui_state.get("trucks", [])
        self.truck_ids = [t["id"] for t in trucks]
        self.truck_selector["values"] = self.truck_ids
        
        # Selection Stability Logic
        if self.active_truck_id and self.active_truck_id in self.truck_ids:
            self.truck_selector.set(self.active_truck_id)
            self._refresh_part_list()
        elif self.truck_ids:
            self.truck_selector.current(0)
            self.active_truck_id = self.truck_ids[0]
            self._refresh_part_list()

    def _on_truck_change(self, event):
        """Updates active truck and re-filters catalog."""
        self.active_truck_id = self.truck_selector.get()
        print(f"UI: Focus Shift -> Upgrades for {self.active_truck_id}")
        self._refresh_part_list()

    def _refresh_part_list(self):
        """Resolves supported parts via MapRunner Bridge."""
        for item in self.tree.get_children():
            self.tree.delete(item)
            
        if not self.active_truck_id:
            return
            
        # Bridge Call: MapRunner (Knowledge) -> UI Entities
        upgrades = self.mapper.maprunner.get_upgrades(self.active_truck_id)
        
        for upg in upgrades:
            self.tree.insert("", "end", values=(
                upg.id, 
                upg.name, 
                upg.map, 
                upg.type
            ))

    def _on_part_double_click(self, event):
        """SAFE EDIT PIPELINE: Part Unlock/Apply."""
        item_id = self.tree.selection()
        if not item_id:
            return
            
        part_data = self.tree.item(item_id[0], "values")
        part_id = part_data[0]
        
        # 1. Validation Stage (Rule: Compatibility Check)
        valid, msg = self.validator.validate_upgrade_availability(
            truck_id=self.active_truck_id,
            upgrade_id=part_id
        )
        
        if not valid:
            messagebox.showerror("Part Filter Blocked", f"Error: {msg}")
            return
            
        # 2. Commit Stage
        if messagebox.askyesno("Confirm", f"Apply upgrade {part_id} to {self.active_truck_id}?"):
            # Dot-Identity path normalization
            path = f"trucks.{self.active_truck_id}.upgrades.{part_id}.discovered"
            self.on_apply_callback(path, True)
