import re
from dataclasses import dataclass

MIN_PASSWORD_LENGTH = 10
_USERNAME = re.compile(r"[a-z0-9._-]{2,32}")


@dataclass(frozen=True)
class User:
    username: str
    is_admin: bool = False


class InvalidCredentials(Exception):
    """Wrong username or password. Deliberately doesn't say which."""


class TooManyAttempts(Exception):
    def __init__(self, retry_after_seconds: int):
        self.retry_after_seconds = retry_after_seconds
        super().__init__(f"Too many failed attempts. Try again in {retry_after_seconds} seconds.")


def normalize_username(name: str | None) -> str:
    return (name or "").strip().lower()


def username_problem(name: str) -> str | None:
    if not _USERNAME.fullmatch(name):
        return "Usernames are 2-32 characters: letters, digits, dot, dash or underscore."
    return None


def password_problem(password: str) -> str | None:
    if len(password) < MIN_PASSWORD_LENGTH:
        return f"Use at least {MIN_PASSWORD_LENGTH} characters."
    return None
