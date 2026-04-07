from dataclasses import dataclass
from typing import List, Optional

@dataclass
class Truck:
    id: str
    name: str
    type: str # heavy, scout, etc.
    regions: List[str]

@dataclass
class Upgrade:
    id: str
    name: str
    vehicle: str
    type: str # engine, suspension, etc.
    region: str
    map: str
