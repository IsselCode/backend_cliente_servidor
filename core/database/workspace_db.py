import json
import sqlite3
from contextlib import contextmanager
from pathlib import Path


class WorkspaceDB:
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

            # Tablas

            conn.executescript(
                """
                    CREATE TABLE IF NOT EXISTS master_config (
                        id INTEGER PRIMARY KEY CHECK (id = 1),
                        master_img BLOB,
                        config_plc TEXT NOT NULL,
                        external_scanner INTEGER NOT NULL DEFAULT 0,
                        ok_piece INTEGER NOT NULL DEFAULT 0,
                        ng_piece INTEGER NOT NULL DEFAULT 0
                    );
                    
                    CREATE TABLE IF NOT EXISTS feature (
                        id TEXT PRIMARY KEY,
                        type TEXT NOT NULL,
                        tag TEXT NULL,
                        x INTEGER NOT NULL,
                        y INTEGER NOT NULL,
                        w INTEGER NOT NULL,
                        h INTEGER NOT NULL,
                        config TEXT NOT NULL
                    );
                            
                    CREATE TABLE IF NOT EXISTS color_img (
                        id TEXT PRIMARY KEY,
                        feature_id TEXT NOT NULL,
                        type INTEGER NOT NULL,
                        img BLOB NOT NULL,
                        FOREIGN KEY(feature_id) REFERENCES feature(id) ON DELETE CASCADE
                    );
                        
                    CREATE TABLE IF NOT EXISTS texture_img (
                        id TEXT PRIMARY KEY,
                        feature_id TEXT NOT NULL,
                        type INTEGER NOT NULL,
                        img BLOB NOT NULL,
                        FOREIGN KEY(feature_id) REFERENCES feature(id) ON DELETE CASCADE
                    );

                    CREATE TABLE IF NOT EXISTS trazability_dbs (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        db_date TEXT NOT NULL UNIQUE,
                        filename TEXT NOT NULL UNIQUE,
                        relative_path TEXT NOT NULL UNIQUE,
                        created_at TEXT NOT NULL
                    );

                """
            )

            # Inserts
            plc_dict = {"ip": "192.168.100.157"}
            plc_json = json.dumps(plc_dict)

            conn.execute("""
                INSERT OR IGNORE INTO master_config (id, config_plc) VALUES (1, ?)
            """, (plc_json,))
