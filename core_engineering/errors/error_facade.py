# [PH4-ERR-002] User-Safe Error Translation Facade
from core_engineering.errors.exceptions import ValidationError
class ErrorFacade:
    """
    Translates internal system failures into user-safe messaging.
    Guarantees no raw Python tracebacks reach the end user.
    """
    
    ERROR_MAP = {
        "VALIDATION_FAILED": "Invalid action. Please check your selection or game context.",
        "INTEGRITY_FAILED": "Save file validation failed. No changes were applied to protect your data.",
        "ROLLBACK": "Operation failed at the disk layer, but your save has been safely restored.",
        "UNKNOWN": "An unexpected system error occurred. Please try again or check the session log."
    }

    @classmethod
    def translate(cls, error: Exception) -> str:
        """Translates an exception instance into a user-friendly string."""
        code = getattr(error, "code", "UNKNOWN")
        base_message = cls.ERROR_MAP.get(code, cls.ERROR_MAP["UNKNOWN"])
        
        # [PH4-ERR-GRAN] Enhanced Granularity
        # We append the actual error message only for safe validation errors.
        if isinstance(error, ValidationError) and str(error):
             return f"{base_message} Details: {str(error)}"
             
        return base_message
