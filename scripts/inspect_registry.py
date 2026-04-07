import json
with open(r'E:\Snow Runner New Tool\core_engineering\data\maprunner_registry.json', 'r') as f:
    data = json.load(f)
    print(list(data.keys()))
    if 'trucks' in data:
        print("Trucks found!")
    if 'upgrades' in data:
        print("Upgrades found!")
