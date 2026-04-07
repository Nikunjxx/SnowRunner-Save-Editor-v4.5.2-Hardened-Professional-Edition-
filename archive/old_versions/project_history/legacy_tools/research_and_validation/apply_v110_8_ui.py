import os
import re

target = r"e:\Snow Runner New Tool\app\snowrunner_editor.py"
with open(target, "r", encoding="utf-8") as f:
    content = f.read()

# 1. Overhaul create_region_tools_tab UI (v110.8 - Logical Steps)
# I will reorganize the feature_specs into two separate frames (Step 2 and Step 3)
# and wrap the region selector in Step 1.

find_tab_build = r'def create_region_tools_tab\(tab, save_path_var, enable_legacy_tabs_var=None, refresh_callback=None\):.*?return \{'
new_tab_build = r'''def create_region_tools_tab(tab, save_path_var, enable_legacy_tabs_var=None, refresh_callback=None):
    """
    v110.8 UI Overhaul: Rearranges features into 3 logical steps.
    Step 1: Save & Region Selection
    Step 2: Map & World Presence (Reveal Map, Map Discovery, Discover All Trucks)
    Step 3: Campaign Progression (Complete Missions, Upgrades)
    """
    container = ttk.Frame(tab)
    container.pack(fill="both", expand=True, padx=10, pady=10)

    # --- STEP 1: Selection ---
    step1_frame = ttk.LabelFrame(container, text=" 1. Select Save & Regions ", padding=(15, 10))
    step1_frame.pack(fill="x", pady=(0, 10))
    
    seasons = [(name, i) for i, name in enumerate(SEASON_LABELS, start=1)]
    maps = [(name, code) for code, name in BASE_MAPS]
    selector = _build_region_selector(
        step1_frame,
        seasons,
        maps,
        base_maps_label="Base Game Maps:",
        base_maps_label_font=("TkDefaultFont", 10, "bold"),
        season_pady=(5, 5),
    )
    season_vars = selector["season_vars"]
    map_vars = selector["map_vars"]
    all_region_vars = selector["all_check_vars"]
    other_season_var = selector["other_var"]
    
    _add_check_all_checkbox(step1_frame, all_region_vars, label="Check All Regions")

    # --- STEPS 2 & 3: Features ---
    feature_vars = {}
    feature_check_vars = []
    
    # Define logical groupings
    step2_specs = [
        {"key": "fog", "label": "Reveal Map (Visuals)", "info": "Instantly reveal the entire fog-of-war for selected regions."},
        {"key": "auto_discovery", "label": "Register Map & Discover Trucks", "info": "Officially registers the map as discovered in your save progress and adds all trucks/trailers to the map registry."},
        {"key": "watchtowers", "label": "Find Watchtowers", "info": "Marks watchtowers as found."},
        {"key": "garages", "label": "Unlock Garages", "info": "Unlocks and registers garage entrance zones."},
        {"key": "fix_recovery", "label": "Fix Recovery System", "info": "Repairs map-to-garage connectivity if the Recover feature is broken."},
    ]
    step3_specs = [
        {"key": "missions", "label": "Complete Missions (Legacy)", "info": "Mark missions as completed.", "legacy": True},
        {"key": "contests", "label": "Complete Contests (Legacy)", "info": "Mark contests as completed.", "legacy": True},
        {"key": "upgrades", "label": "Register Upgrades", "info": "Adds upgrades to the discovery registry."},
    ]

    def _build_step_frame(parent, title, specs):
        frame = ttk.LabelFrame(parent, text=f" {title} ", padding=(15, 10))
        frame.pack(fill="x", pady=5)
        
        row_box = ttk.Frame(frame)
        row_box.pack(anchor="w")
        
        for idx, spec in enumerate(specs):
            var = tk.IntVar(value=0)
            feature_vars[spec["key"]] = var
            feature_check_vars.append(var)
            
            r = idx // 2
            c = (idx % 2) * 3 # 3 columns per feature (cb, label, info)
            
            cb = ttk.Checkbutton(row_box, variable=var)
            cb.grid(row=r, column=c, sticky="w", pady=2)
            
            lbl = ttk.Label(row_box, text=spec["label"])
            lbl.grid(row=r, column=c+1, sticky="w", padx=(5, 15), pady=2)
            
            info_badge = tk.Label(row_box, text="i", width=2, relief="ridge", bd=1, bg="#f4d6d6", fg="#b00000", cursor="question_arrow")
            info_badge.grid(row=r, column=c+2, sticky="w", pady=2)
            _attach_hover_tooltip(info_badge, spec.get("info", ""))

    _build_step_frame(container, "2. Unlock Map & World Presence", step2_specs)
    _build_step_frame(container, "3. Complete Objectives & Progress", step3_specs)

    # --- APPLY ZONE ---
    apply_frame = ttk.Frame(container)
    apply_frame.pack(fill="x", pady=(15, 0))
    
    def _collect_region_payload():
        selected_seasons = _collect_checked_values(season_vars)
        _append_other_season_int(selected_seasons, other_season_var)
        selected_maps = _collect_checked_values(map_vars)
        selected_regions = [SEASON_ID_MAP[s] for s in selected_seasons if s in SEASON_ID_MAP]
        selected_regions.extend(selected_maps)
        
        deduped = list(dict.fromkeys(selected_regions))
        return deduped

    def _on_apply_regions():
        path = save_path_var.get()
        if not path or not os.path.exists(path):
            messagebox.showerror("Error", "Please select a valid save file first.")
            return

        regions = _collect_region_payload()
        if not regions:
            # v110.8 Error Handling Check
            messagebox.showerror("Selection Error", "Please select at least one region in Step 1 first.")
            return

        selected_features = {k: v.get() for k, v in feature_vars.items()}
        if not any(selected_features.values()):
            messagebox.showwarning("Selection Warning", "Please select at least one feature from Step 2 or Step 3.")
            return

        # Ensure Step 2 (Registration) is applied if Step 3 (Missions) is checked
        if (selected_features.get("missions") or selected_features.get("upgrades")) and not selected_features.get("auto_discovery"):
            if messagebox.askyesno("Discovery Required", "Missions/Upgrades work best when the map is Registered (Discovery). Would you like to enable 'Register Map & Discover Trucks' as well?"):
                feature_vars["auto_discovery"].set(1)
                selected_features["auto_discovery"] = 1

        res = None
        if selected_features.get("fog"):
            res = generate_revealed_fog(path, regions)
        if selected_features.get("auto_discovery"):
            res = discover_world_objects(path, regions)
        if selected_features.get("missions") or selected_features.get("contests"):
            res = complete_missions(path, regions)
        
        if refresh_callback: refresh_callback()
        if res: messagebox.showinfo("Success", "Selected regions updated successfully!")

    apply_btn = ttk.Button(apply_frame, text="ðŸ›¡ï¸ Process All Selected Steps", command=_on_apply_regions, width=35)
    apply_btn.pack(anchor="center")
    
    return {'''

content = re.sub(find_tab_build, new_tab_build, content, flags=re.DOTALL)

# 2. Version Bump to v110.8
content = content.replace('APP_VERSION = 110.7', 'APP_VERSION = 110.8')

with open(target, "w", encoding="utf-8") as f:
    f.write(content)

print("Applied v110.8 UI overhaul.")
