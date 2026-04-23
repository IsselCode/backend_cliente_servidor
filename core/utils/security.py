import uuid
from datetime import timedelta
from typing import Any
import jwt

from core.errors.exceptions import AuthenticationError
from core.utils.datetimes import utc_now

class TokenManager:
    def __init__(self, secret_key: str, expiration_minutes: int):
        self.secret_key = secret_key
        self.expiration_minutes = expiration_minutes
        self.refresh_expiration_days = 7
        self.algorithm = "HS256"

    def create_access_token(self, dp: str, username: str, role: str, uid: str):
        now = utc_now()
        payload = {
            "jti": str(uuid.uuid4()),
            "iat": int(now.timestamp()),
            "exp": int( (now + timedelta(minutes=self.expiration_minutes)).timestamp() ),
            "type": "access",
            "display_name": dp,
            "sub": username,
            "role": role,
            "uid": uid,
        }
        return jwt.encode(payload, self.secret_key, algorithm=self.algorithm)

    def create_refresh_token(self, uid: str) -> tuple[str, str, str]:
        now = utc_now()
        jti = str(uuid.uuid4())
        expires_at = now + timedelta(days=self.refresh_expiration_days)
        payload = {
            "jti": jti,
            "iat": int(now.timestamp()),
            "exp": int(expires_at.timestamp()),
            "type": "refresh",
            "uid": uid,
        }

        token = jwt.encode(payload, self.secret_key, algorithm=self.algorithm)

        return token, jti, expires_at.isoformat()

    def decode_access_token(self, token: str) -> dict[str, Any]:
        payload = self._decode_and_validate(token)

        if payload.get("type") != "access":
            raise AuthenticationError("El token no es de tipo AccessToken")

        return payload

    def decode_refresh_token(self, token: str) -> dict[str, Any]:
        payload = self._decode_and_validate(token)

        if payload.get("type") != "refresh":
            raise AuthenticationError("El token no es de tipo RefreshToken")

        return payload

    def _decode_and_validate(self, token: str):
        try:
            decoded = jwt.decode(
                token,
                self.secret_key,
                algorithms=[self.algorithm],
                options={
                    "require": ["exp", "iat", "jti", "type", "uid"],
                },
            )
        except jwt.ExpiredSignatureError as exc:
            raise AuthenticationError("Token expirado") from exc
        except jwt.InvalidTokenError as exc:
            raise AuthenticationError("Token invalido") from exc

        return decoded