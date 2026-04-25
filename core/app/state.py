"""
Contenedor de dependencias compartidas de la aplicacion.

Reune configuracion y servicios ya creados para acceder a ellos desde FastAPI
sin recrearlos en cada modulo.
"""

from dataclasses import dataclass

from core.app.settings import AppSettings
from core.database.database import Database
from core.database.repositories.refresh_token_repository import RefreshTokenRepository
from core.database.repositories.user_repository import UserRepository
from core.services.mdns_service import MDNSService
from core.services.password_service import PasswordService
from core.utils.security import TokenManager


@dataclass(slots=True)
class AppState:
    mdns_service: MDNSService
    settings: AppSettings
    database: Database
    users: UserRepository
    refresh_tokens: RefreshTokenRepository
    password_service: PasswordService
    token_manager: TokenManager
