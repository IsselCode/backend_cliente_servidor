import shutil
from pathlib import Path

from core.app.settings import AppSettings
from core.database.workspace_db import WorkspaceDB


def workspace_dir(settings: AppSettings, workspace_key: str) -> Path:
    return settings.workspaces_dir / workspace_key


def workspace_db_path(settings: AppSettings, workspace_key: str) -> Path:
    return workspace_dir(settings, workspace_key) / "workspace.db"


def workspace_trazability_dir(settings: AppSettings, workspace_key: str) -> Path:
    return workspace_dir(settings, workspace_key) / "trazability"


def workspace_images_dir(settings: AppSettings, workspace_key: str) -> Path:
    return workspace_dir(settings, workspace_key) / "images"


def workspace_trazability_db_filename(db_date: str) -> str:
    return f"{db_date}.db"


def workspace_trazability_db_relative_path(db_date: str) -> Path:
    return Path("trazability") / workspace_trazability_db_filename(db_date)


def workspace_trazability_db_path(settings: AppSettings, workspace_key: str, db_date: str) -> Path:
    return workspace_dir(settings, workspace_key) / workspace_trazability_db_relative_path(db_date)


def workspace_relative_path(settings: AppSettings, workspace_key: str, relative_path: str) -> Path:
    return workspace_dir(settings, workspace_key) / Path(relative_path)


def ensure_workspace_storage(settings: AppSettings, workspace_key: str) -> None:
    root_dir = workspace_dir(settings, workspace_key)
    root_dir.mkdir(parents=True, exist_ok=True)
    workspace_trazability_dir(settings, workspace_key).mkdir(parents=True, exist_ok=True)
    workspace_images_dir(settings, workspace_key).mkdir(parents=True, exist_ok=True)


def initialize_workspace_db(settings: AppSettings, workspace_key: str) -> WorkspaceDB:
    ensure_workspace_storage(settings, workspace_key)
    workspace_db = WorkspaceDB(workspace_db_path(settings, workspace_key))
    workspace_db.initialize()
    return workspace_db


def delete_workspace_storage(settings: AppSettings, workspace_key: str) -> None:
    root_dir = workspace_dir(settings, workspace_key)
    if root_dir.is_dir():
        shutil.rmtree(root_dir)
    elif root_dir.exists():
        root_dir.unlink()
