"""
Configuracion general del backend.

Agrupa valores como el nombre de la aplicacion y el puerto, leyendolos desde
variables de entorno con valores por defecto para desarrollo.
"""

import os
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
    jwt_secret: str
    jwt_expiration_minutes: int
    bootstrap_admin_username: str
    bootstrap_admin_password: str

    @classmethod
    def from_env(cls) -> "AppSettings":
        base_path = Path(__file__).resolve().parent.parents[2]
        default_database_path = base_path / "app.db"

        return cls(
            app_name=os.getenv("APP_NAME", "Backend cliente servidor"),
            app_port=int(os.getenv("APP_PORT", 8000)),
            api_prefix=os.getenv("API_PREFIX", "/api/v1"),
            database_path=Path(os.getenv("DATABASE_PATH", str(default_database_path))),
            jwt_secret=os.getenv("JWT_SECRET", "prueba-llave-ultra-secreta"),
            jwt_expiration_minutes=int(os.getenv("JWT_EXPIRATION_MINUTES", 60)),
            bootstrap_admin_username=os.getenv("BOOTSTRAP_ADMIN_USERNAME", "admin"),
            bootstrap_admin_password=os.getenv("BOOTSTRAP_ADMIN_PASSWORD", "admin123"),
        )
