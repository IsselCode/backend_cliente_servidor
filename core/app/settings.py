"""
Configuracion general del backend.

Agrupa valores como el nombre de la aplicacion y el puerto, leyendolos desde
variables de entorno con valores por defecto para desarrollo.
"""

import os
from math import isfinite
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()


@dataclass(slots=True)
class AppSettings:
    app_name: str
    app_port: int
    api_prefix: str
    database_path: Path
    workspaces_dir: Path
    jwt_secret: str
    jwt_expiration_minutes: int
    bootstrap_admin_username: str
    bootstrap_admin_password: str
    webcam_index: int = 0
    camera_capture_fps: float = 30
    camera_stop_timeout: float = 5
    stream_fps: float = 10
    stream_jpeg_quality: int = 85
    stream_send_timeout: float = 5
    stream_auth_timeout: float = 10
    master_image_light_settle_time: float = 0.25
    master_image_capture_timeout: float = 5
    master_image_discard_frames: int = 2

    def __post_init__(self) -> None:
        for name in ("stream_send_timeout", "stream_auth_timeout"):
            value = getattr(self, name)
            if not isfinite(value) or value <= 0:
                raise ValueError(f"{name} debe ser positivo y finito")

    @classmethod
    def from_env(cls) -> "AppSettings":
        base_path = Path(__file__).resolve().parents[2]
        default_database_path = base_path / "app.db"
        default_workspaces_dir = base_path / "workspaces"

        return cls(
            app_name=os.getenv("APP_NAME", "Backend cliente servidor"),
            app_port=int(os.getenv("APP_PORT", 8000)),
            api_prefix=os.getenv("API_PREFIX", "/api/v1"),
            database_path=Path(os.getenv("DATABASE_PATH", str(default_database_path))),
            workspaces_dir=Path(os.getenv("WORKSPACES_DIR", str(default_workspaces_dir))),
            jwt_secret=os.getenv("JWT_SECRET", "prueba-llave-ultra-secreta"),
            jwt_expiration_minutes=int(os.getenv("JWT_EXPIRATION_MINUTES", 60)),
            bootstrap_admin_username=os.getenv("BOOTSTRAP_ADMIN_USERNAME", "admin"),
            bootstrap_admin_password=os.getenv("BOOTSTRAP_ADMIN_PASSWORD", "admin123"),
            webcam_index=int(os.getenv("WEBCAM_INDEX", "0")),
            camera_capture_fps=float(os.getenv("CAMERA_CAPTURE_FPS", "30")),
            camera_stop_timeout=float(os.getenv("CAMERA_STOP_TIMEOUT", "5")),
            stream_fps=float(os.getenv("STREAM_FPS", "10")),
            stream_jpeg_quality=int(os.getenv("STREAM_JPEG_QUALITY", "85")),
            stream_send_timeout=float(os.getenv("STREAM_SEND_TIMEOUT", "5")),
            stream_auth_timeout=float(os.getenv("STREAM_AUTH_TIMEOUT", "10")),
            master_image_light_settle_time=float(os.getenv("MASTER_IMAGE_LIGHT_SETTLE_TIME", "0.25")),
            master_image_capture_timeout=float(os.getenv("MASTER_IMAGE_CAPTURE_TIMEOUT", "5")),
            master_image_discard_frames=int(os.getenv("MASTER_IMAGE_DISCARD_FRAMES", "2")),
        )
