"""Echo utility modules."""

__all__ = [
    "setup_logging",
    "ensure_directories",
    "cleanup_temp_files",
]


def __getattr__(name):
    """Lazy imports to avoid circular dependencies."""
    if name == "setup_logging":
        from echo.utils.logging import setup_logging

        return setup_logging
    elif name == "ensure_directories":
        from echo.utils.helpers import ensure_directories

        return ensure_directories
    elif name == "cleanup_temp_files":
        from echo.utils.helpers import cleanup_temp_files

        return cleanup_temp_files
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
