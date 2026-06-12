from typing import Any

from core.database.workspace_db import WorkspaceDB
from core.utils.datetimes import utc_now_iso


class WorkspaceTrazabilityDBRepository:
    def __init__(self, workspace_db: WorkspaceDB) -> None:
        self.workspace_db = workspace_db

    def create(
        self,
        *,
        db_date: str,
        filename: str,
        relative_path: str,
    ) -> dict[str, Any]:
        payload = {
            "db_date": db_date,
            "filename": filename,
            "relative_path": relative_path,
            "created_at": utc_now_iso(),
        }

        with self.workspace_db.connection() as connection:
            connection.execute(
                """
                INSERT INTO trazability_dbs (db_date, filename, relative_path, created_at)
                VALUES (:db_date, :filename, :relative_path, :created_at)
                """,
                payload,
            )

        return self.find_by_date(db_date)

    def find_by_date(self, db_date: str) -> dict[str, Any] | None:
        with self.workspace_db.connection() as connection:
            row = connection.execute(
                """
                SELECT id, db_date, filename, relative_path, created_at
                FROM trazability_dbs
                WHERE db_date = ?
                """,
                (db_date,),
            ).fetchone()
        return dict(row) if row else None

    def list_all(self) -> list[dict[str, Any]]:
        with self.workspace_db.connection() as connection:
            rows = connection.execute(
                """
                SELECT id, db_date, filename, relative_path, created_at
                FROM trazability_dbs
                ORDER BY db_date ASC
                """
            ).fetchall()
        return [dict(row) for row in rows]

