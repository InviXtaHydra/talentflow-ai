"""Private file storage on a local volume. Files are addressed by random opaque keys; original
filenames are never used as paths, and nothing in this directory is served by a web server."""

import contextlib
import os
import secrets
from pathlib import Path

from app.core.config import get_settings


class LocalStorage:
    def __init__(self, root: str) -> None:
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True)

    def _path(self, key: str) -> Path:
        if not key.isalnum():
            raise ValueError("invalid storage key")
        return self.root / key[:2] / key

    def save(self, data: bytes) -> str:
        key = secrets.token_hex(24)
        path = self._path(key)
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "wb") as handle:
            handle.write(data)
        os.chmod(path, 0o600)
        return key

    def read(self, key: str) -> bytes:
        return self._path(key).read_bytes()

    def delete(self, key: str | None) -> None:
        if not key:
            return
        with contextlib.suppress(FileNotFoundError):
            self._path(key).unlink()


_storage: LocalStorage | None = None


def get_storage() -> LocalStorage:
    global _storage
    if _storage is None:
        _storage = LocalStorage(get_settings().storage_dir)
    return _storage


def set_storage(storage: LocalStorage | None) -> None:
    global _storage
    _storage = storage
