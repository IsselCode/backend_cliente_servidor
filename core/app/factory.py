from fastapi import FastAPI

from core.app.lifecycle import app_lifespan
from core.app.settings import AppSettings
from core.app.state import AppState
from core.services.mdns_service import MDNSService


def create_app() -> FastAPI:
    settings = AppSettings.from_env()
    mdns_service = MDNSService()

    app = FastAPI(title=settings.app_name, lifespan=app_lifespan)
    app.state.container = AppState(
        mdns_service=mdns_service,
        settings=settings
    )

    return app