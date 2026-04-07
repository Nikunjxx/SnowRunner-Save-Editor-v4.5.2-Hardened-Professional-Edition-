from typing import List, Dict, Any, Optional
from .base import BasePlugin
from .context import PluginContext

class PluginManager:
    """
    v110.70 Hardened Plugin Orchestrator.
    Manages lifecycle, sandboxing, and circuit breakers for feature modules.
    """
    
    def __init__(self, integrity_manager: Any, ui_callbacks: Dict[str, Any]):
        self._manager = integrity_manager
        self._context = PluginContext(integrity_manager, ui_callbacks)
        self._plugins: Dict[str, BasePlugin] = {}
        self._disabled_plugins: set = set()

    def rebind_manager(self, new_integrity_manager: Any):
        """[v111.00] Updates the plugin system to use the new active manager."""
        self._manager = new_integrity_manager
        self._context.update_manager(new_integrity_manager)
        print("[PluginManager] Context synchronized with new manager instance.")

    def register_plugin(self, plugin: BasePlugin):
        """Registers a new plugin with the manager and context."""
        if plugin.id in self._plugins:
            print(f"[PluginManager] Warning: Duplicate plugin ID '{plugin.id}' ignored.")
            return

        # 1. [v110.70] Sandboxing Guard: Prevent direct engine access
        if hasattr(plugin, "manager"):
            raise AssertionError(f"Plugin '{plugin.id}' violation: Direct manager access forbidden.")
            
        # 2. Provide context
        plugin.register(self._context)
        
        # 3. Add to registry
        self._plugins[plugin.id] = plugin
        print(f"[PluginManager] Registered: {plugin.display_name} ({plugin.id})")

    def get_plugin(self, plugin_id: str) -> Optional[BasePlugin]:
        """[v111.00] Safe access to a specific plugin instance."""
        return self._plugins.get(plugin_id)

    def get_all_plugins(self) -> List[BasePlugin]:
        """[v111.00] Returns all registered and active plugins."""
        return sorted(
            [p for p in self._plugins.values() if p.id not in self._disabled_plugins],
            key=lambda x: x.display_name
        )

    def run_plugin(self, plugin_id: str) -> Dict[str, Any]:
        """
        [v111.00] Transactional Execution Gateway.
        Wraps mutation plugins in an IntegrityManager transaction.
        """
        plugin = self.get_plugin(plugin_id)
        if not plugin:
            return {"success": False, "error": f"Plugin '{plugin_id}' not found."}
        
        if plugin_id in self._disabled_plugins:
            return {"success": False, "error": "Plugin is currently disabled (Circuit Breaker)."}

        print(f"[PluginManager] Executing: {plugin.id} ({plugin.plugin_type})")
        
        try:
            if plugin.plugin_type == "mutation":
                # External Transaction Control (v111.00 Requirement)
                with self._manager.transaction() as tx_id:
                    result = plugin.execute(self._context)
                    result["tx_id"] = tx_id
                    return result
            else:
                # Read-only execution
                return plugin.execute(self._context)
                
        except Exception as e:
            err_msg = f"Plugin execution failed: {str(e)}"
            self.disable_plugin(plugin_id, reason=err_msg)
            return {"success": False, "error": err_msg}

    def disable_plugin(self, plugin_id: str, reason: str = "Unknown"):
        """Soft-disables a plugin for the remainder of the session."""
        if plugin_id in self._plugins and plugin_id not in self._disabled_plugins:
            self._disabled_plugins.add(plugin_id)
            print(f"[PluginManager] CIRCUIT_BREAKER: Disabled '{plugin_id}'. Reason: {reason}")
            self._context.set_app_status(f"⚠️ Plugin '{plugin_id}' disabled due to error.", timeout_ms=8000)

    def get_plugins_by_category(self, category: str) -> List[BasePlugin]:
        """
        [v110.70] Discovery Gate.
        Includes only active (non-disabled) plugins, sorted by name.
        """
        filtered = [
            p for p in self._plugins.values() 
            if p.category.upper() == category.upper() and p.id not in self._disabled_plugins
        ]
        return sorted(filtered, key=lambda x: x.display_name)

    def trigger_refresh_all(self):
        """Dispatches refresh event to all active plugins with circuit breaker protection."""
        for plugin in self.get_plugins_by_category("ADVANCED") + self.get_plugins_by_category("INTELLIGENCE"):
            try:
                plugin.refresh()
            except Exception as e:
                self.disable_plugin(plugin.id, reason=str(e))

    def trigger_folder_load(self, folder_path: str):
        """Dispatches folder_load event to all active plugins."""
        # Use unfiltered values here to ensure background logic runs even if UI tab isn't active,
        # but still protect with breaker.
        for plugin in list(self._plugins.values()):
            if plugin.id in self._disabled_plugins: continue
            try:
                plugin.on_folder_load(folder_path)
            except Exception as e:
                self.disable_plugin(plugin.id, reason=str(e))
