from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerifyMismatchError

from core.errors.exceptions import AuthenticationError


class PasswordService:
    def __init__(self) -> None:
        self.ph = PasswordHasher()

    def hash_password(self, password: str) -> str:
        return self.ph.hash(password)

    def verify_password(self, password: str, hashed_password: str) -> bool:
        try:
            return self.ph.verify(hashed_password, password)
        except VerifyMismatchError:
            return False
        except InvalidHashError:
            raise AuthenticationError("El formato del hash es invalido")
