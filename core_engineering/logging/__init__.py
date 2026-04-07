# core_engineering/logging/__init__.py
from .logger import AppLogger

# Global Singleton [PH4-LOG-002]
logger = AppLogger()
