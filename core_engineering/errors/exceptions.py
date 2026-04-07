# [PH4-ERR-001] Structured Application Exceptions
class AppError(Exception):
    """Base application exception with error codes and severity."""
    code = "UNKNOWN"
    severity = "ERROR"

    def __init__(self, message=None, context=None):
        super().__init__(message)
        # Contextual metadata (e.g. field_path, file_path)
        self.context = context or {}

class ValidationError(AppError):
    """Rejection from the FieldValidator layer."""
    code = "VALIDATION_FAILED"
    severity = "WARNING"

class IntegrityError(AppError):
    """Bit-drift or structural violation during Save/Load."""
    code = "INTEGRITY_FAILED"
    severity = "ERROR"

class TransactionError(AppError):
    """Failure during the Commit/Atomic Replace phase."""
    code = "ROLLBACK"
    severity = "CRITICAL"
