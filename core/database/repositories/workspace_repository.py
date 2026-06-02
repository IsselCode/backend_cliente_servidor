from typing import Any

from core.database.database import Database
from core.utils.datetimes import utc_now_iso


class WorkspaceRepository:
    def __init__(self, database: Database) -> None:
        self.database = database

    def create(self, *, workspace_key: str, display_name: str) -> dict[str, Any]:
        payload = {
            "workspace_key": workspace_key,
            "display_name": display_name,
            "created_at": utc_now_iso(),
        }

        with self.database.connection() as connection:
            connection.execute(
                """
                INSERT INTO vision_workspace_dbs (workspace_key, display_name, created_at)
                VALUES (:workspace_key, :display_name, :created_at)
                """,
                payload,
            )

        return self.find_by_workspace_key(workspace_key)

    def find_by_workspace_key(self, workspace_key: str) -> dict[str, Any] | None:
        with self.database.connection() as connection:
            row = connection.execute(
                """
                SELECT id, workspace_key, display_name, created_at
                FROM vision_workspace_dbs
                WHERE workspace_key = ?
                """,
                (workspace_key,),
            ).fetchone()
        return dict(row) if row else None

    def list_all(self) -> list[dict[str, Any]]:
        with self.database.connection() as connection:
            rows = connection.execute(
                """
                SELECT id, workspace_key, display_name, created_at
                FROM vision_workspace_dbs
                ORDER BY id ASC
                """
            ).fetchall()
        return [dict(row) for row in rows]

    def update_by_workspace_key(
        self,
        workspace_key: str,
        *,
        new_workspace_key: str | None = None,
        display_name: str | None = None,
    ) -> dict[str, Any] | None:
        current_workspace = self.find_by_workspace_key(workspace_key)
        if not current_workspace:
            return None

        payload = {
            "workspace_key": workspace_key,
            "new_workspace_key": new_workspace_key if new_workspace_key is not None else current_workspace["workspace_key"],
            "display_name": display_name if display_name is not None else current_workspace["display_name"],
        }

        with self.database.connection() as connection:
            connection.execute(
                """
                UPDATE vision_workspace_dbs
                SET workspace_key = :new_workspace_key,
                    display_name = :display_name
                WHERE workspace_key = :workspace_key
                """,
                payload,
            )

        return self.find_by_workspace_key(payload["new_workspace_key"])

    def delete_by_workspace_key(self, workspace_key: str) -> bool:
        with self.database.connection() as connection:
            cursor = connection.execute(
                "DELETE FROM vision_workspace_dbs WHERE workspace_key = ?",
                (workspace_key,),
            )
        return cursor.rowcount > 0
