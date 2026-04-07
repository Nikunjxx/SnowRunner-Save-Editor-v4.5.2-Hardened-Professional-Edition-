import json
import csv
import os

def build():
    print("Building MapRunner Registry from cached CSV and statics...")
    registry = {
        "metadata": {
            "version": "1.0",
            "source": "MapRunner offline cache"
        },
        "regions": {
            "US_01": {"name": "Michigan", "type": "base"},
            "US_02": {"name": "Alaska", "type": "base"},
            "RU_02": {"name": "Taymyr", "type": "base"},
            "RU_03": {"name": "Kola Peninsula", "type": "dlc", "season": 1},
            "US_04": {"name": "Yukon", "type": "dlc", "season": 2},
            "US_03": {"name": "Wisconsin", "type": "dlc", "season": 3},
            "RU_04": {"name": "Amur", "type": "dlc", "season": 4},
            "RU_05": {"name": "Don", "type": "dlc", "season": 5},
            "US_06": {"name": "Maine", "type": "dlc", "season": 6},
            "US_07": {"name": "Tennessee", "type": "dlc", "season": 7},
            "RU_08": {"name": "Glades", "type": "dlc", "season": 8},
            "US_09": {"name": "Ontario", "type": "dlc", "season": 9},
            "US_10": {"name": "British Columbia", "type": "dlc", "season": 10},
            "US_11": {"name": "Scandinavia", "type": "dlc", "season": 11},
            "US_12": {"name": "North Carolina", "type": "dlc", "season": 12},
            "RU_13": {"name": "Almaty", "type": "dlc", "season": 13},
            "US_14": {"name": "Austria", "type": "dlc", "season": 14},
            "US_15": {"name": "Quebec", "type": "dlc", "season": 15},
            "US_16": {"name": "Washington", "type": "dlc", "season": 16},
            "RU_17": {"name": "Zurdania", "type": "dlc", "season": 17}
        },
        "objectives": {}
    }

    csv_path = r"C:\Users\gupta\snowrunner_save_editor_data\.snowrunner_editor_maprunner_data.csv"
    
    if not os.path.exists(csv_path):
        print(f"ERROR: Cached CSV not found at {csv_path}")
        return

    count = 0
    with open(csv_path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            region = row.get("region", "")
            if not region:
                continue
                
            if region not in registry["objectives"]:
                registry["objectives"][region] = []
                
            registry["objectives"][region].append(row)
            count += 1
            
    print(f"Extracted {len(registry['regions'])} regions.")
    print(f"Extracted {count} objectives targeting {len(registry['objectives'])} regions.")
        
    out_path = r"E:\Snow Runner New Tool\core_engineering\data\maprunner_registry.json"
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(registry, f, indent=4)
        
    print(f"Registry successfully written to {out_path}")

if __name__ == "__main__":
    build()
