from typing import Dict, Any, List, Optional, Protocol, Union

class IntegrityManagerInterface(Protocol):
    """Protocol for the core IntegrityManager to avoid circular imports."""
    def execute_feature(self, feature: str, payload: Dict[str, Any]) -> Dict[str, Any]: ...
    def peek_folder(self, folder_path: str) -> Dict[str, Any]: ...
    def get_progression_analytics(self) -> Dict[str, Any]: ...
    def save_context(self) -> Dict[str, Any]: ...

class PluginContext:
    """
    v110.70 Hardened Context Bridge.
    Protects the core IntegrityManager while providing plugins with 
    safe, permissioned access to session data and external analysis.
    """
    
    # [v110.70] Canonical Feature -> Permission Source of Truth
    FEATURE_PERMISSIONS = {
        "map_unlock": ["fog"],
        "objective_complete": ["complete", "sts"],
        "save_compare": [], # Read-only
        "diagnostic_check": ["read"],
        "dashboard_analytics": ["read"]
    }

    def __init__(self, manager: IntegrityManagerInterface, ui_callbacks: Dict[str, Any]):
        self._manager = manager
        self._ui_callbacks = ui_callbacks

    def update_manager(self, new_manager: IntegrityManagerInterface):
        """[v111.00] Rebind the context to a new active manager instance."""
        self._manager = new_manager

    def execute_feature(self, feature: str, payload: Dict[str, Any], plugin: Any) -> Dict[str, Any]:
        """
        [v110.70] Permissioned Execution Wrapper.
        Validates both feature mapping and plugin 'write' capability.
        """
        if feature not in self.FEATURE_PERMISSIONS:
            raise PermissionError(f"[{plugin.id}] Attempted unmapped feature: {feature}")

        required_perms = self.FEATURE_PERMISSIONS[feature]
        
        # Enforce 'write' permission if feature has engine side-effects
        if required_perms and not getattr(plugin, "permissions", {}).get("write", False):
            # Only allow if the required_perms is strictly 'read' and the plugin has it.
            # But the user rule is: if FEATURE_PERMISSIONS[feature] is not empty, it requires write.
            raise PermissionError(f"[{plugin.id}] Feature '{feature}' requires write permissions.")

        for perm in required_perms:
            if perm not in plugin.permissions:
                raise PermissionError(f"[{plugin.id}] Missing permission '{perm}' for feature: {feature}")

        try:
            return self._manager.execute_feature(feature, payload)
        except Exception as e:
            raise RuntimeError(f"[{plugin.id}] Engine error during {feature}: {e}")

    def peek_external_save(self, folder_path: str, plugin: Any) -> Dict[str, Any]:
        """
        [v110.70] Safe Bridge to Engine Peek Logic.
        Allows read-only analysis of external save folders.
        """
        if "read" not in plugin.permissions:
             raise PermissionError(f"[{plugin.id}] Missing 'read' permission for external peek.")
        return self._manager.peek_folder(folder_path)

    def get_active_snapshot(self, plugin: Any) -> Dict[str, Any]:
        """[v110.80] Returning canonical Save Snapshot (Progress + Vehicles)."""
        if "read" not in getattr(plugin, "permissions", {}):
            raise PermissionError(f"[{plugin.id}] Missing 'read' permission.")
        return self._manager.get_active_snapshot()

    def get_progression_data(self, plugin: Any) -> Dict[str, Any]:
        """[v110.70] Returning detailed regional analytics for Dashboard."""
        if "read" not in getattr(plugin, "permissions", {}):
            raise PermissionError(f"[{plugin.id}] Missing 'read' permission.")
        return self._manager.get_progression_analytics()

    def set_app_status(self, message: str, timeout_ms: int = 5000):
        """Bridge to the main UI status bar."""
        if "set_status" in self._ui_callbacks:
            self._ui_callbacks["set_status"](message, timeout_ms=timeout_ms)

    @property
    def save_folder(self) -> Optional[str]:
        """Safe access to the current target folder (read-only)."""
        return getattr(self._manager, "target_folder", None)

    def get_save_registry(self) -> Dict[str, Any]:
        """[v110.70] Safe access to indexed file registry (fog, sts, etc.)."""
        # Return a copy to prevent in-place mutation of the manager's state
        ctx = getattr(self._manager, "save_context", {})
        return {k: (v.copy() if isinstance(v, dict) else v) for k, v in ctx.items()}

    def get_region_metadata(self) -> Dict[str, List[str]]:
        """[v110.70] Safe access to map/region distribution data."""
        resolver = getattr(self._manager, "resolver", None)
        return getattr(resolver, "REGION_LEVELS", {})
