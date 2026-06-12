import sqlite3
from contextlib import contextmanager
from pathlib import Path


class TrazabilityDB:
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
        self.database_path.parent.mkdir(parents=True, exist_ok=True)

        with self.connection() as conn:
            conn.executescript(
                """
                    CREATE TABLE IF NOT EXISTS Trazabilidad (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        escaneo TEXT,
                        fecha TEXT DEFAULT (date('now','localtime')),
                        hora  TEXT DEFAULT (time('now','localtime')),
                        resultado INTEGER,
                        datos TEXT,
                        imagen TEXT
                    );
                """
            )
