"""
Contenedor de dependencias compartidas de la aplicacion.

Reune configuracion y servicios ya creados para acceder a ellos desde FastAPI
sin recrearlos en cada modulo.
"""

from dataclasses import dataclass

from core.app.settings import AppSettings
from core.services.mdns_service import MDNSService


@dataclass(slots=True)
class AppState:
    mdns_service: MDNSService
    settings: AppSettings
