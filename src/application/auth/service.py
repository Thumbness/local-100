from ...domain.auth.user import InvalidCredentials, TooManyAttempts, User, normalize_username
from ..ports import PasswordHasher, UserDirectory
from .throttle import LoginThrottle


class AuthService:
    def __init__(self, users: UserDirectory, passwords: PasswordHasher,
                 ip_throttle: LoginThrottle | None = None, user_throttle: LoginThrottle | None = None):
        self._users = users
        self._passwords = passwords
        # Tight limit per address; looser per username, so guessing one account from many addresses is
        # slowed without letting a stranger lock a real user out after a handful of tries
        self._ip_throttle = ip_throttle or LoginThrottle(max_failures=5)
        self._user_throttle = user_throttle or LoginThrottle(max_failures=20)

    def has_users(self) -> bool:
        return self._users.any_users()

    def login(self, username: str, password: str, client: str) -> User:
        """Return the user if the credentials are right. Raises InvalidCredentials or TooManyAttempts."""
        name = normalize_username(username)
        wait = max(self._ip_throttle.retry_after(client), self._user_throttle.retry_after(name))
        if wait:
            raise TooManyAttempts(wait)

        stored = self._users.find(name) if name else None
        if stored is None:
            self._passwords.burn(password)
            ok = False
        else:
            ok = self._passwords.verify(stored.password_hash, password)

        if not ok:
            self._ip_throttle.record_failure(client)
            self._user_throttle.record_failure(name)
            raise InvalidCredentials()

        self._ip_throttle.reset(client)
        self._user_throttle.reset(name)
        return User(username=stored.username, is_admin=stored.is_admin)

    def user_for(self, username: str) -> User | None:
        """The current record for a signed-in user, or None if they've since been removed."""
        stored = self._users.find(normalize_username(username))
        return User(username=stored.username, is_admin=stored.is_admin) if stored else None
