"""
Ciclo de vida de la aplicacion FastAPI.

Registra mDNS al arrancar. Al finalizar detiene el monitor antes de cerrar
el PLC y libera mDNS. El polling se activa explicitamente para la inferencia.
"""

from asyncio import to_thread
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
        try:
            await to_thread(state.plc_trigger_monitor.stop)
            await to_thread(state.plc_service.cerrar)
        finally:
            await state.mdns_service.stop()
