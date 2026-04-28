import sqlite3
from contextlib import contextmanager
from pathlib import Path


class Database:
    def __init__(self, database_path: Path):
        self.database_path = database_path

    @contextmanager
    def connection(self):
        conn = sqlite3.connect(self.database_path)
        conn.row_factory = sqlite3.Row
        conn.execute('PRAGMA foreign_keys = ON')
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    def initialize(self):
        # self.database_path: ruta completa de la base de datos
        # parent: apunta a la ultima carpeta
        # mkdir: crea la carpeta
        #   * parents: crea las carpetas padre en caso de que falten
        #   * exist_ok: si ya existe la ruta, evita mandar una excepción
        self.database_path.parent.mkdir(parents=True, exist_ok=True)

        with self.connection() as conn:
            conn.executescript(
                """
                    CREATE TABLE IF NOT EXISTS users (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        uid TEXT NOT NULL UNIQUE,
                        username TEXT NOT NULL UNIQUE,
                        display_name TEXT NOT NULL,
                        password_hash TEXT NOT NULL,
                        role TEXT NOT NULL,
                        is_active INTEGER NOT NULL DEFAULT 1,
                        created_at TEXT NOT NULL
                    );
                    
                    CREATE TABLE IF NOT EXISTS refresh_tokens (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        jti TEXT NOT NULL UNIQUE,
                        user_uid TEXT NOT NULL,
                        token_hash TEXT NOT NULL,
                        expires_at TEXT NOT NULL,
                        revoked_at TEXT NULL,
                        created_at TEXT NOT NULL,
                        FOREIGN KEY(user_uid) REFERENCES users(uid) ON DELETE CASCADE
                    );
                    
                    CREATE TABLE IF NOT EXISTS audit_logs (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        user_uid TEXT NULL,
                        username TEXT NULL,
                        display_name TEXT NULL,
                        role TEXT NULL,
                        event_key TEXT NULL,
                        enabled INTEGER NOT NULL DEFAULT 0,
                        error_code TEXT NULL,
                        error_detail TEXT NULL,
                        error_meta TEXT NULL,
                        tipo TEXT NOT NULL,
                        info TEXT NOT NULL,
                        method TEXT NOT NULL,
                        path TEXT NOT NULL,
                        query_params TEXT NULL,
                        status_code INTEGER NOT NULL,
                        client_ip TEXT NULL,
                        duration_ms REAL NOT NULL,
                        created_at TEXT NOT NULL
                    );
                    
                    CREATE TABLE IF NOT EXISTS business_settings (
                        id INTEGER PRIMARY KEY CHECK (id = 1),
                        user_created INTEGER NOT NULL DEFAULT 1,
                        user_deleted INTEGER NOT NULL DEFAULT 1,
                        user_modified INTEGER NOT NULL DEFAULT 1,
                        login INTEGER NOT NULL DEFAULT 1,
                        logout INTEGER NOT NULL DEFAULT 1
                    );
                """
            )

            conn.execute("""
                INSERT INTO business_settings (
                    id, user_created, user_deleted, user_modified,
                    login, logout
                )
                SELECT ?, ?, ?, ?, ?, ?
                WHERE NOT EXISTS (SELECT 1 FROM business_settings WHERE id = 1)
            """, (1, 1, 1, 1, 1, 1,))