"""
Ciclo de vida de la aplicacion FastAPI.

Define que debe ocurrir cuando el backend inicia y cuando se apaga; por ahora
registra el servicio mDNS al arrancar y lo libera al finalizar.
"""

from contextlib import asynccontextmanager
from typing import AsyncIterator

from fastapi import FastAPI

from core.app.state import AppState


@asynccontextmanager
async def app_lifespan(app: FastAPI) -> AsyncIterator[None]:
    state: AppState = app.state.container

    await state.mdns_service.start(state.settings.app_port)
    try:
        yield
    finally:
        await state.mdns_service.stop()
