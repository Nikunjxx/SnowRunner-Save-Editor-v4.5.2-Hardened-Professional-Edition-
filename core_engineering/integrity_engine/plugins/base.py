from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional
import tkinter as tk

class BasePlugin(ABC):
    """
    Abstract Base Class for all SnowRunner Save Editor plugins.
    v111.00 Architecture: Mandatory execution and metadata interface.
    """
    
    @property
    def api_version(self) -> str:
        """[v110.70] Plugin API compatibility version."""
        return "1.1"

    @property
    def capabilities(self) -> Dict[str, Any]:
        """[v110.70] Formal feature/permission introspection."""
        return {
            "id": self.id,
            "permissions": self.permissions,
            "category": self.category,
            "type": self.plugin_type,
            "description": self.description,
            "primary_action": self.primary_action_name
        }

    @property
    @abstractmethod
    def id(self) -> str:
        """Unique identifier for the plugin (e.g. 'dashboard')."""
        pass

    @property
    @abstractmethod
    def display_name(self) -> str:
        """Human-readable name for the UI tab."""
        pass

    @property
    @abstractmethod
    def category(self) -> str:
        """Notebook category: 'CORE', 'ADVANCED', 'INTELLIGENCE', 'SYSTEM'."""
        pass

    @property
    @abstractmethod
    def plugin_type(self) -> str:
        """'read' for analytics, 'mutation' for save-modifying features."""
        pass

    @property
    @abstractmethod
    def description(self) -> str:
        """Detailed description of what the plugin does."""
        pass

    @property
    @abstractmethod
    def primary_action_name(self) -> str:
        """Name of the button action (e.g. 'Reveal Map')."""
        pass

    @property
    def permissions(self) -> Dict[str, Any]:
        """[v110.70] Updated permission dictionary (e.g. {'read': True, 'write': False, 'fog': True})."""
        return {"read": True}

    @abstractmethod
    def register(self, context: Any):
        """Called during PluginManager initialization."""
        pass

    @abstractmethod
    def render(self, parent: tk.Frame):
        """Builds the plugin's UI inside the provided parent frame."""
        pass

    @abstractmethod
    def refresh(self):
        """Called during global UI refresh cycles."""
        pass

    @abstractmethod
    def execute(self, context: Any) -> Dict[str, Any]:
        """
        [v111.00] Mandatory execution entry point.
        Should return: {"success": bool, "summary": str, "error": Optional[str]}
        """
        pass

    def on_folder_load(self, folder_path: str):
        """Optional hook called when a new save folder is selected."""
        pass
