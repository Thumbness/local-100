import math
import threading
import time
from typing import Callable


class LoginThrottle:
    """Locks a key (an IP address, a username) after too many recent failures. In memory, so one process only."""

    def __init__(self, max_failures: int = 5, window_seconds: int = 900, lockout_seconds: int = 900,
                 clock: Callable[[], float] = time.monotonic):
        self._max = max_failures
        self._window = window_seconds
        self._lockout = lockout_seconds
        self._clock = clock
        self._lock = threading.Lock()
        self._failures: dict[str, list[float]] = {}
        self._locked_until: dict[str, float] = {}

    def retry_after(self, key: str) -> int:
        """Seconds until `key` may try again; 0 if it may try now."""
        with self._lock:
            remaining = self._locked_until.get(key, 0.0) - self._clock()
            if remaining > 0:
                return math.ceil(remaining)
            self._locked_until.pop(key, None)
            return 0

    def record_failure(self, key: str) -> None:
        with self._lock:
            now = self._clock()
            recent = [t for t in self._failures.get(key, []) if now - t < self._window]
            recent.append(now)
            if len(recent) >= self._max:
                self._locked_until[key] = now + self._lockout
                self._failures.pop(key, None)
            else:
                self._failures[key] = recent
            self._prune(now)

    def reset(self, key: str) -> None:
        with self._lock:
            self._failures.pop(key, None)
            self._locked_until.pop(key, None)

    def _prune(self, now: float) -> None:
        # Keeps memory bounded if someone sprays random usernames
        if len(self._failures) + len(self._locked_until) < 5000:
            return
        self._failures = {k: v for k, v in self._failures.items() if v and now - v[-1] < self._window}
        self._locked_until = {k: t for k, t in self._locked_until.items() if t > now}
