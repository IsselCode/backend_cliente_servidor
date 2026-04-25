import hashlib
from typing import Any

from core.database.database import Database
from core.utils.datetimes import utc_now_iso


class RefreshTokenRepository:
    def __init__(self, database: Database) -> None:
        self.database = database

    @staticmethod
    def _hash_token(token: str) -> str:
        return hashlib.sha256(token.encode("utf-8")).hexdigest()

    def create(self, *, jti: str, user_uid: str, token: str, expires_at: str) -> None:
        with self.database.connection() as connection:
            connection.execute(
                """
                INSERT INTO refresh_tokens (jti, user_uid, token_hash, expires_at, revoked_at, created_at)
                VALUES (?, ?, ?, ?, NULL, ?)
                """,
                (jti, user_uid, self._hash_token(token), expires_at, utc_now_iso()),
            )

    def find_active_by_token(self, token: str) -> dict[str, Any] | None:
        token_hash = self._hash_token(token)
        with self.database.connection() as connection:
            row = connection.execute(
                """
                SELECT id, jti, user_uid, token_hash, expires_at, revoked_at, created_at
                FROM refresh_tokens
                WHERE token_hash = ? AND revoked_at IS NULL AND expires_at > ?
                """,
                (token_hash, utc_now_iso()),
            ).fetchone()
        return dict(row) if row else None

    def revoke_by_jti(self, jti: str) -> bool:
        with self.database.connection() as connection:
            cursor = connection.execute(
                "UPDATE refresh_tokens SET revoked_at = ? WHERE jti = ? AND revoked_at IS NULL",
                (utc_now_iso(), jti),
            )
        return cursor.rowcount > 0