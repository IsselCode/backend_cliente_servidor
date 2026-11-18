"""Vista previa autenticada por WebSocket; sin controles HTTP de camara."""

import asyncio
import logging

import anyio
from fastapi import WebSocket, WebSocketDisconnect
from starlette.websockets import WebSocketState

from core.app.enums import UserRole
from core.app.state import AppState
from core.contracts.camera import CameraError
from core.errors.exceptions import AuthenticationError
from core.services.frame_stream_service import (
    FrameSubscription, StreamClosedError, StreamPacket,
)
from src.dependencies.context import authenticate_access_token
from src.routers.base import APIRouter
from src.schemas.camera import FrameMessage

router = APIRouter(prefix="/camera", tags=["camera"])
logger = logging.getLogger(__name__)


class _ProtocolError(Exception):
    pass


async def _authenticate(websocket: WebSocket, state: AppState) -> None:
    """Bearer para clientes nativos; primer mensaje para clientes web sin headers."""
    authorization = websocket.headers.get("authorization")
    if authorization is not None:
        scheme, separator, token = authorization.partition(" ")
        if not separator or scheme.lower() != "bearer" or not token.strip():
            raise AuthenticationError("Authorization header is invalid")
        token = token.strip()
    else:
        message = await asyncio.wait_for(websocket.receive_json(), timeout=state.settings.stream_auth_timeout)
        if not isinstance(message, dict) or message.get("type") != "authenticate":
            raise AuthenticationError("Se requiere authenticate como primer mensaje")
        token = message.get("access_token")
        if not isinstance(token, str) or not token.strip():
            raise AuthenticationError("Se requiere un access_token")
    auth = await asyncio.to_thread(authenticate_access_token, token, state)
    if auth.role not in {role.value for role in UserRole}:
        raise AuthenticationError("User role is invalid")
    websocket.state.auth_context = auth


async def _send_packet(websocket: WebSocket, packet: StreamPacket) -> None:
    metadata = FrameMessage.from_frame(packet.frame)
    await websocket.send_json(metadata.model_dump(mode="json"))
    await websocket.send_bytes(packet.frame.jpeg)


async def _send_packets(websocket: WebSocket, subscription: FrameSubscription, timeout: float) -> None:
    # Un solo emisor mantiene juntos los metadatos y el JPEG de cada frame.
    while True:
        packet = await subscription.receive()
        await asyncio.wait_for(_send_packet(websocket, packet), timeout=timeout)


async def _wait_disconnect(websocket: WebSocket) -> None:
    while True:
        message = await websocket.receive()
        if message["type"] == "websocket.disconnect":
            return
        raise _ProtocolError("El canal solo recibe la autenticacion inicial")


@router.websocket("/stream")
async def stream(websocket: WebSocket) -> None:
    state: AppState = websocket.app.state.container
    subscription = None
    tasks: list[asyncio.Task] = []
    close_code, reason = 1000, ""
    await websocket.accept()
    try:
        try:
            await _authenticate(websocket, state)
        except (AuthenticationError, TimeoutError, ValueError, KeyError):
            close_code, reason = 1008, "Autenticacion requerida o invalida"
            return
        subscription = await state.frame_stream_service.subscribe()
        tasks = [
            asyncio.create_task(_send_packets(websocket, subscription, state.settings.stream_send_timeout)),
            asyncio.create_task(_wait_disconnect(websocket)),
        ]
        done, _ = await asyncio.wait(tasks, return_when=asyncio.FIRST_COMPLETED)
        for task in done:
            task.result()
    except WebSocketDisconnect:
        pass
    except _ProtocolError:
        close_code, reason = 1008, "No se admiten comandos de camara por este canal"
    except TimeoutError:
        close_code, reason = 1013, "El cliente no recibe los datos a tiempo; reconecta"
    except StreamClosedError:
        close_code, reason = 1001, "Transmision cerrada"
    except CameraError:
        close_code, reason = 1011, "Webcam no disponible"
        logger.exception("Fallo de captura en el WebSocket")
    except Exception:
        close_code, reason = 1011, "Fallo de transmision"
        logger.exception("Fallo del WebSocket de imagenes")
    finally:
        # Starlette puede cancelar el scope al desconectarse el cliente.
        # Completar la liberacion aunque esa cancelacion siga activa.
        with anyio.CancelScope(shield=True):
            for task in tasks:
                task.cancel()
            if tasks:
                await asyncio.gather(*tasks, return_exceptions=True)
            if subscription is not None:
                await state.frame_stream_service.unsubscribe(subscription)
            if websocket.application_state is WebSocketState.CONNECTED:
                try:
                    await websocket.close(code=close_code, reason=reason)
                except (WebSocketDisconnect, RuntimeError, OSError):
                    pass
