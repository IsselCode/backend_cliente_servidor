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