from werkzeug.security import check_password_hash, generate_password_hash


class WerkzeugPasswordHasher:
    """Salted, slow password hashes (Werkzeug's default scheme). Implements the PasswordHasher port."""

    def __init__(self):
        self._dummy_hash = generate_password_hash("not-a-real-password")

    def hash(self, password: str) -> str:
        return generate_password_hash(password)

    def verify(self, password_hash: str, password: str) -> bool:
        return check_password_hash(password_hash, password)

    def burn(self, password: str) -> None:
        check_password_hash(self._dummy_hash, password)
