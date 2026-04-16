"""
Configuracion general del backend.

Agrupa valores como el nombre de la aplicacion y el puerto, leyendolos desde
variables de entorno con valores por defecto para desarrollo.
"""

import os
from dataclasses import dataclass
from dotenv import load_dotenv

load = load_dotenv()

@dataclass(slots=True)
class AppSettings:
    app_name: str
    app_port: int

    @classmethod
    def from_env(cls) -> "AppSettings":
        return cls(
            app_name=os.getenv("APP_NAME", "Backend cliente servidor"),
            app_port=int(os.getenv("APP_PORT", 8000)),
        )
