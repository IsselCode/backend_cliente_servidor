from fastapi import FastAPI, APIRouter

from src.routers.auth import router as auth_router
from src.routers.users import router as users_router


def register_routers(app: FastAPI, api_prefix: str) -> None:
    api_router = APIRouter(prefix=api_prefix)
    api_router.include_router(auth_router)
    api_router.include_router(users_router)
    app.include_router(api_router)
