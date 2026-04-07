import re
import yaml
import os
import logging
from typing import List

logger = logging.getLogger("InterpretationEngine")

class NoiseFilter:
    """[PH2-RUL-002] Regex-based transient field exclusion."""
    
    _patterns: List[str] = []
    _initialized = False

    @classmethod
    def _initialize(cls):
        if cls._initialized:
            return
        try:
            # [PH2-RUL-006] Absolute Path Resolution
            engine_dir = os.path.dirname(os.path.abspath(__file__))
            rules_path = os.path.join(engine_dir, "rules.yaml")
            with open(rules_path, "r") as f:
                rules = yaml.safe_load(f)
                cls._patterns = rules.get("noise", [])
            cls._initialized = True
        except Exception as e:
            logger.error(f"NOISE_FILTER_INIT_FAIL: {str(e)}")
            cls._patterns = []

    @classmethod
    def is_noise(cls, path: str) -> bool:
        cls._initialize()
        # [PH2-RUL-003] Using re.search for robust pattern matching
        return any(re.search(p, path) for p in cls._patterns)
