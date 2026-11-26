"""Locked, atomic JSON file storage shared by local repository adapters."""

import json
import os
import tempfile
from pathlib import Path

from filelock import FileLock


class JsonFileStore:
    """Subclasses hold ``lock`` around the entire read/modify/write operation."""

    def __init__(self, path: Path):
        self.path = path
        path.parent.mkdir(parents=True, exist_ok=True)
        self.lock = FileLock(str(path) + ".lock", timeout=10)

    def _write(self, data: dict) -> None:
        fd, name = tempfile.mkstemp(
            dir=self.path.parent, prefix=f".{self.path.stem}-", suffix=".tmp"
        )
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as stream:
                json.dump(data, stream, ensure_ascii=False, indent=2)
                stream.flush()
                os.fsync(stream.fileno())
            os.replace(name, self.path)
        finally:
            if os.path.exists(name):
                os.unlink(name)

