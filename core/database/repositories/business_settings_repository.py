from typing import Any

from core.database.database import Database


class BusinessSettingsRepository:
    def __init__(self, database: Database) -> None:
        self.database = database

    def get(self) -> dict[str, Any]:
        with self.database.connection() as connection:
            row = connection.execute(
                """
                SELECT
                    id,
                    user_created,
                    user_deleted,
                    user_modified,
                    login,
                    logout,
                FROM business_settings
                WHERE id = 1
                """
            ).fetchone()
        if row is None:
            raise RuntimeError("Business settings row is not initialized")
        return dict(row)

    def update(self, **fields: Any) -> dict[str, Any]:
        allowed_fields = {
            "user_created",
            "user_deleted",
            "user_modified",
            "login",
            "logout",
        }
        updates = {key: value for key, value in fields.items() if key in allowed_fields}
        if not updates:
            return self.get()

        assignments = ", ".join(f"{key} = :{key}" for key in updates)
        payload = {
            key: int(value) if isinstance(value, bool) else value
            for key, value in updates.items()
        }
        payload["id"] = 1

        with self.database.connection() as connection:
            connection.execute(
                f"UPDATE business_settings SET {assignments} WHERE id = :id",
                payload,
            )
        return self.get()