import structlog


def get_logger(name: str) -> structlog.BoundLogger:
    """Wrapper around project logger."""
    return structlog.get_logger(name)
