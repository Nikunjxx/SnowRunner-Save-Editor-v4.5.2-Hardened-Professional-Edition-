class SnowRunnerEngineError(Exception):
    """Base exception for all SnowRunner Save Engine errors."""
    pass

class IntegrityError(SnowRunnerEngineError):
    """Raised when file integrity checks (null bytes, JSON syntax, encoding) fail."""
    pass

class SchemaError(SnowRunnerEngineError):
    """Raised when a save file fails the Canonical Schema Contract (Missing REQUIRED fields)."""
    pass

class BinaryError(SnowRunnerEngineError):
    """Raised when ZLIB decompress/recompress or round-trip validation fails."""
    pass

class TransactionError(SnowRunnerEngineError):
    """Raised when an atomic transaction, pre-commit hook, or rollback fails."""
    pass

class RegistryError(SnowRunnerEngineError):
    """Raised when game mapping or ID normalization fails."""
    pass
