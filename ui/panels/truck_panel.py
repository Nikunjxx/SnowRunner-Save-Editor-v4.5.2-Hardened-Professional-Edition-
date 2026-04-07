# [PH3-UI-011] Truck Management Panel (STABLE)
import tkinter as tk
from tkinter import ttk, messagebox

class TruckPanel:
    """
    Control Layer for Warehouse Management.
    REFINEMENTS:
    - [PH3-UI-REF-001] SELECTION STABILITY.
    - [PH3-UI-REF-002] Path Normalization (Identity Dot Notation).
    """
    
    def __init__(self, parent, mapper, validator, on_apply_callback):
        self.parent = parent
        self.mapper = mapper
        self.validator = validator
        self.on_apply_callback = on_apply_callback
        
        self.selected_truck_id = None # [REFINEMENT] Persistent Focus
        
        self._setup_view()

    def _setup_view(self):
        """Builds static layout."""
        frame = ttk.LabelFrame(self.parent, text="Warehouse Fleet (Identity)", padding=10)
        frame.pack(fill="both", expand=True, padx=10, pady=10)
        
        self.tree = ttk.Treeview(frame, columns=("ID", "Name", "Type", "Status"), show="headings")
        self.tree.heading("ID", text="Truck ID")
        self.tree.heading("Name", text="Game Name")
        self.tree.heading("Type", text="Class")
        self.tree.heading("Status", text="Status")
        
        self.tree.column("ID", width=150)
        self.tree.column("Name", width=200)
        self.tree.column("Type", width=100)
        self.tree.column("Status", width=100)
        
        self.tree.pack(side="left", fill="both", expand=True)
        
        self.scrollbar = ttk.Scrollbar(frame, orient=tk.VERTICAL, command=self.tree.yview)
        self.tree.configure(yscroll=self.scrollbar.set)
        self.scrollbar.pack(side="right", fill="y")
        
        # Interaction Triggers
        self.tree.bind("<<TreeviewSelect>>", self._on_select_change)
        self.tree.bind("<Double-1>", self._on_truck_double_click)

    def _on_select_change(self, event):
        """Updates internal selection tracker on user click."""
        selection = self.tree.selection()
        if selection:
            item_data = self.tree.item(selection[0], "values")
            self.selected_truck_id = item_data[0] # The canonical truck_id
            print(f"UI: Focus Shift -> {self.selected_truck_id}")

    def render(self, resolved_truck_list: list):
        """
        Populates UI from resolved state.
        [REFINEMENT] Pursues selection stability.
        """
        for item in self.tree.get_children():
            self.tree.delete(item)
            
        target_item_to_select = None
        
        for truck in resolved_truck_list:
            status = "Unlocked ✅" if truck["is_unlocked"] else "Locked ❌"
            item = self.tree.insert("", "end", values=(
                truck["id"], 
                truck["name"], 
                truck["type"], 
                status
            ))
            
            # [REFINEMENT] Re-apply Selection Focus
            if truck["id"] == self.selected_truck_id:
                target_item_to_select = item
        
        if target_item_to_select:
            self.tree.selection_set(target_item_to_select)
            self.tree.see(target_item_to_select)

    def _on_truck_double_click(self, event):
        """SAFE EDIT PIPELINE: Context-Aware Toggle."""
        item_id = self.tree.selection()
        if not item_id:
            return
            
        truck_data = self.tree.item(item_id[0], "values")
        truck_id = truck_data[0]
        is_currently_unlocked = "Unlocked" in truck_data[3]
        
        new_value = not is_currently_unlocked
        
        # [PH4-EXEC-GATED] No manual validation. 
        # Rely on SafeExecutor + ValidationRegistry in the Engine.
        self.on_apply_callback(f"trucks.{truck_id}.isUnlocked", new_value)
