import uuid
from typing import Any

from core.app.enums import UserRole
from core.database.database import Database
from core.utils import datetimes

class UserRepository:
    def __init__(self, database: Database) -> None:
        self.database = database

    def create_user(self, username: str, dp_name: str, password_hash: str, role: UserRole) -> dict[str, Any]:
        payload = {
            "uid": str(uuid.uuid4()),
            "username": username,
            "display_name": dp_name,
            "password_hash": password_hash,
            "role": role.value,
            "created_at": datetimes.utc_now_iso(),
        }

        with self.database.connection() as connection:
            connection.execute(
                """
                    INSERT INTO users (uid, username, display_name, password_hash, role, created_at)
                    VALUES (:uid, :username, :display_name, :password_hash, :role, :created_at)
                """,
                payload,
            )

        return self.find_by_username(username)

    def find_by_username(self, username: str) -> dict[str, Any] | None:
        with self.database.connection() as connection:
            row = connection.execute(
                """
                SELECT id, uid, username, display_name, password_hash, role, is_active, created_at
                FROM users
                WHERE username = ?
                """,
                (username,),
            ).fetchone()
        return dict(row) if row else None

    def find_by_uid(self, uid: str) -> dict[str, Any] | None:
        with self.database.connection() as connection:
            row = connection.execute(
                """
                SELECT id, uid, username, display_name, password_hash, role, is_active, created_at
                FROM users
                WHERE uid = ?
                """,
                (uid,),
            ).fetchone()
        return dict(row) if row else None

    def list_all(self) -> list[dict[str, Any]]:
        with self.database.connection() as connection:
            rows = connection.execute(
                """
                SELECT id, uid, username, display_name, password_hash, role, is_active, created_at
                FROM users
                ORDER BY id ASC
                """
            ).fetchall()
        return [dict(row) for row in rows]

    def update_by_uid(
        self,
        uid: str,
        *,
        username: str | None = None,
        display_name: str | None = None,
        password_hash: str | None = None,
        role: UserRole | None = None,
        is_active: bool | None = None,
    ) -> dict[str, Any] | None:
        current_user = self.find_by_uid(uid)
        if not current_user:
            return None

        payload = {
            "uid": uid,
            "username": username if username is not None else current_user["username"],
            "display_name": display_name if display_name is not None else current_user["display_name"],
            "password_hash": password_hash if password_hash is not None else current_user["password_hash"],
            "role": role.value if role is not None else current_user["role"],
            "is_active": int(is_active) if is_active is not None else current_user["is_active"],
        }
        with self.database.connection() as connection:
            connection.execute(
                """
                UPDATE users
                SET username = :username,
                    display_name = :display_name,
                    password_hash = :password_hash,
                    role = :role,
                    is_active = :is_active
                WHERE uid = :uid
                """,
                payload,
            )
        return self.find_by_uid(uid)

    def delete_by_uid(self, uid: str) -> bool:
        with self.database.connection() as connection:
            cursor = connection.execute("DELETE FROM users WHERE uid = ?", (uid,))
        return cursor.rowcount > 0

    def search_by_name(self, name: str) -> list[dict[str, Any]]:
        search_term = f"%{name.strip().lower()}%"
        with self.database.connection() as connection:
            rows = connection.execute(
                """
                SELECT id, uid, username, display_name, password_hash, role, is_active, created_at
                FROM users
                WHERE lower(username) LIKE ? OR lower(display_name) LIKE ?
                ORDER BY id ASC
                """,
                (search_term, search_term),
            ).fetchall()
        return [dict(row) for row in rows]
