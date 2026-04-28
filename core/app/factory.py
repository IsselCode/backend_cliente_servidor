"""
Construccion principal de la aplicacion FastAPI.

Carga la configuracion, crea los servicios base y guarda el estado compartido
que otros modulos usan durante el ciclo de vida del backend.
"""

from fastapi import FastAPI
from pydantic_core.core_schema import dataclass_args_schema

from core.app.lifecycle import app_lifespan
from core.app.settings import AppSettings
from core.app.state import AppState
from core.database.bootstrap import bootstrap_admin_user
from core.database.database import Database
from core.database.repositories.audit_log_repository import AuditLogRepository
from core.database.repositories.business_settings_repository import BusinessSettingsRepository
from core.database.repositories.refresh_token_repository import RefreshTokenRepository
from core.database.repositories.user_repository import UserRepository
from core.errors.handlers import register_exception_handlers
from core.services.audit_service import AuditService
from core.services.mdns_service import MDNSService
from core.services.password_service import PasswordService
from core.utils.security import TokenManager
from src.routers import register_routers


def create_app() -> FastAPI:
    # Configuraciones
    settings = AppSettings.from_env()
    database = Database(settings.database_path)
    database.initialize()

    # Repositorios
    users = UserRepository(database)
    refresh_tokens = RefreshTokenRepository(database)
    business_settings = BusinessSettingsRepository(database)
    audit_logs = AuditLogRepository(database)

    # Servicios
    mdns_service = MDNSService()
    password_service = PasswordService()
    audit_service = AuditService(
        business_settings = business_settings,
        audit_logs = audit_logs,
    )

    # Utilidades
    token_manager = TokenManager(
        secret_key = settings.jwt_secret,
        expiration_minutes = settings.jwt_expiration_minutes)

    # Bootstrap
    bootstrap_admin_user(
        users = users,
        password_service = password_service,
        username = settings.bootstrap_admin_username,
        password = settings.bootstrap_admin_password
    )

    app = FastAPI(title=settings.app_name, lifespan=app_lifespan)
    app.state.container = AppState(
        mdns_service=mdns_service,
        settings=settings,
        database=database,
        users = users,
        refresh_tokens = refresh_tokens,
        password_service = password_service,
        token_manager = token_manager,
        business_settings = business_settings,
        audit_logs = audit_logs,
        audit_service = audit_service,
    )


    register_exception_handlers(app)
    register_routers(app, settings.api_prefix)


    return app
