"""Application logs with bounded file storage and safe exception details."""

import logging
import traceback
from logging.handlers import RotatingFileHandler

from app.core.config import BACKEND_ROOT, Settings


class SafeExceptionFormatter(logging.Formatter):
    def formatException(self, exc_info):
        # Exception messages (especially SQL errors) can contain credentials or values.
        exception_type, _, tb = exc_info
        return "".join(traceback.format_tb(tb)) + exception_type.__name__


def configure_logging(settings: Settings) -> None:
    """Configure only the app namespace; leave server/third-party loggers alone."""
    path = settings.owl_log_file
    if not path.is_absolute():
        path = BACKEND_ROOT / path
    path.parent.mkdir(parents=True, exist_ok=True)
    logger = logging.getLogger("app")
    logger.setLevel(settings.owl_log_level)
    logger.propagate = False
    configuration = (
        str(path.resolve()), settings.owl_log_max_bytes, settings.owl_log_backup_count
    )
    # App factories/reloads must not accumulate duplicate handlers or open files.
    for handler in list(logger.handlers):
        if getattr(handler, "owl_configuration", None) is not None:
            if handler.owl_configuration == configuration:
                return
            logger.removeHandler(handler)
            handler.close()

    formatter = SafeExceptionFormatter(
        "%(asctime)s %(levelname)s %(name)s %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S%z",
    )
    file_handler = RotatingFileHandler(
        path,
        maxBytes=settings.owl_log_max_bytes,
        backupCount=settings.owl_log_backup_count,
        encoding="utf-8",
    )
    file_handler.setFormatter(formatter)
    file_handler.owl_configuration = configuration
    logger.addHandler(file_handler)

    # Reuse a single console handler even if the log file configuration changes.
    if not any(getattr(handler, "owl_console", False) for handler in logger.handlers):
        console = logging.StreamHandler()
        console.setFormatter(formatter)
        console.owl_console = True
        logger.addHandler(console)


def request_route(request) -> str:
    """Use route templates so URLs, query parameters and user IDs are not logged."""
    route = request.scope.get("route")
    return getattr(route, "path", "<unmatched>")

