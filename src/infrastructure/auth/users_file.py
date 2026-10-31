import json
import os
import threading
from pathlib import Path

from ...application.ports import StoredUser
from ...domain.auth.user import normalize_username


class JsonUserDirectory:
    """Users in a JSON file: {"users": {"alice": {"password_hash": "...", "admin": true}}}.

    Re-read whenever the file changes, so adding or removing a user takes effect without a restart.
    A missing or unreadable file means no users, so nobody can sign in (it fails closed).
    """

    def __init__(self, path):
        self._path = Path(path)
        self._lock = threading.Lock()
        self._cache: dict[str, StoredUser] = {}
        self._stamp = None

    # ---- UserDirectory port -----------------------------------------------------------------
    def find(self, username: str) -> StoredUser | None:
        with self._lock:
            return self._load().get(normalize_username(username))

    def any_users(self) -> bool:
        with self._lock:
            return bool(self._load())

    # ---- management (used by the command-line tool) -----------------------------------------
    def usernames(self) -> list[StoredUser]:
        with self._lock:
            return sorted(self._load().values(), key=lambda u: u.username)

    def add(self, username: str, password_hash: str, is_admin: bool) -> None:
        with self._lock:
            data = self._read_raw()
            data.setdefault("users", {})[normalize_username(username)] = {
                "password_hash": password_hash,
                "admin": bool(is_admin),
            }
            self._write_raw(data)

    def remove(self, username: str) -> bool:
        with self._lock:
            data = self._read_raw()
            removed = data.get("users", {}).pop(normalize_username(username), None) is not None
            if removed:
                self._write_raw(data)
            return removed

    # ---- internals --------------------------------------------------------------------------
    def _load(self) -> dict[str, StoredUser]:
        try:
            stat = self._path.stat()
        except FileNotFoundError:
            self._cache, self._stamp = {}, None
            return self._cache
        stamp = (stat.st_mtime_ns, stat.st_size)
        if stamp != self._stamp:
            try:
                users = self._read_raw().get("users", {})
                self._cache = {
                    normalize_username(name): StoredUser(
                        username=normalize_username(name),
                        password_hash=entry["password_hash"],
                        is_admin=bool(entry.get("admin", False)),
                    )
                    for name, entry in users.items()
                }
            except (ValueError, KeyError, AttributeError, TypeError):
                self._cache = {}
            self._stamp = stamp
        return self._cache

    def _read_raw(self) -> dict:
        if not self._path.is_file():
            return {}
        return json.loads(self._path.read_text(encoding="utf-8"))

    def _write_raw(self, data: dict) -> None:
        self._path.parent.mkdir(parents=True, exist_ok=True)
        temp = self._path.with_suffix(".tmp")
        temp.write_text(json.dumps(data, indent=2), encoding="utf-8")
        try:
            os.chmod(temp, 0o600)  # best effort; not meaningful on Windows
        except OSError:
            pass
        os.replace(temp, self._path)
