from datetime import date, time, datetime, timedelta, UTC
from typing import Any

from core.database.database import Database
from core.utils.datetimes import utc_now_iso, utc_now


class AuditLogRepository:
    def __init__(self, database: Database) -> None:
        self.database = database

    def create(
        self, *,
        user_uid: str | None, username: str | None, display_name: str | None,
        role: str | None, event_key: str | None = None, enabled: bool = False,
        error_code: str | None = None, error_detail: str | None = None,
        error_meta: str | None = None, tipo: str, info: str,
        method: str, path: str, query_params: str | None, status_code: int,
        client_ip: str | None,duration_ms: float,
    ) -> None:
        with self.database.connection() as connection:
            connection.execute(
                """
                INSERT INTO audit_logs (
                    user_uid, username, display_name, role, event_key,
                    enabled, error_code, error_detail, error_meta, tipo, 
                    info, method, path, query_params, status_code,
                    client_ip, duration_ms, created_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    user_uid, username, display_name, role, event_key,
                    int(enabled), error_code, error_detail, error_meta,
                    tipo, info, method, path, query_params, status_code,
                    client_ip, duration_ms, utc_now_iso(),
                ),
            )

    def list_recent(self, limit: int = 50) -> list[dict[str, Any]]:
        with self.database.connection() as connection:
            rows = connection.execute(
                """
                SELECT
                    id, user_uid, username, display_name, role,
                    event_key, enabled, error_code, error_detail,
                    error_meta, tipo, info, method, path, query_params,
                    status_code, client_ip, duration_ms, created_at
                FROM audit_logs
                WHERE enabled = 1
                ORDER BY id DESC
                LIMIT ?
                """,
                (limit,)
            ).fetchall()
        return [dict(row) for row in rows]

    def list_by_date_range(self, start_date: date, end_date: date, limit: int = 200) -> list[dict[str, Any]]:
        start_at = datetime.combine(start_date, time.min, tzinfo=UTC).isoformat()
        end_at = datetime.combine(end_date + timedelta(days=1), time.min, tzinfo=UTC).isoformat()
        with self.database.connection() as connection:
            rows = connection.execute(
                """
                SELECT
                    id, user_uid, username, display_name, role,
                    event_key, enabled, error_code, error_detail,
                    error_meta, tipo, info, method, path, query_params,
                    status_code, client_ip, duration_ms, created_at
                FROM audit_logs
                WHERE unixepoch(created_at) >= unixepoch(?)
                AND unixepoch(created_at) < unixepoch(?)
                ORDER BY unixepoch(created_at) DESC, id DESC
                LIMIT ?
                """,
                (start_at, end_at, limit,)
            ).fetchall()
        return [dict(row) for row in rows]

    def delete_older_than_days(self, retention_days: int) -> int:
        cutoff = utc_now().timestamp() - (retention_days * 24 * 60 * 60)
        with self.database.connection() as connection:
            cursor = connection.execute(
                """
                DELETE FROM audit_logs
                WHERE unixepoch(created_at) < ?
                """,
                (int(cutoff),),
            )
        return cursor.rowcount
