"""Vista previa JPEG compartida; sin dependencias de FastAPI ni de vision."""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass
from math import isfinite

import cv2

from core.contracts.camera import CameraError, CameraFrame, EncodedFrame
from core.services.camera_service import CameraService

logger = logging.getLogger(__name__)


class StreamClosedError(RuntimeError):
    pass


@dataclass(frozen=True, slots=True)
class StreamPacket:
    frame: EncodedFrame


class FrameSubscription:
    """Conserva solo la ultima vista previa pendiente para cada consumidor."""

    def __init__(self) -> None:
        self._preview: StreamPacket | None = None
        self._ready = asyncio.Event()
        self._error: Exception | None = None

    async def receive(self) -> StreamPacket:
        while True:
            if self._error is not None:
                raise self._error
            if self._preview is not None:
                packet, self._preview = self._preview, None
                return packet
            self._ready.clear()
            await self._ready.wait()

    def offer_preview(self, packet: StreamPacket) -> None:
        if self._error is None:
            self._preview = packet
            self._ready.set()

    def fail(self, error: Exception) -> None:
        if self._error is None:
            self._error = error
            self._preview = None
            self._ready.set()


class FrameStreamService:
    """Un productor para todos los suscriptores, creado solo bajo demanda.

    Los metodos async pertenecen al event loop del servidor. El primer cliente
    inicia la camara y el ultimo la detiene, respetando capturas individuales
    que aun esten pendientes.
    """

    def __init__(self, camera: CameraService, *, fps: float = 10, jpeg_quality: int = 85) -> None:
        if not isfinite(fps) or fps <= 0:
            raise ValueError("fps debe ser positivo y finito")
        if isinstance(jpeg_quality, bool) or not isinstance(jpeg_quality, int) or not 1 <= jpeg_quality <= 100:
            raise ValueError("jpeg_quality debe estar entre 1 y 100")
        self._camera = camera
        self._interval = 1 / fps
        self._jpeg_quality = jpeg_quality
        self._subscriptions: set[FrameSubscription] = set()
        self._producer: asyncio.Task | None = None
        self._lock = asyncio.Lock()
        self._closed = False

    async def subscribe(self) -> FrameSubscription:
        async with self._lock:
            if self._closed:
                raise StreamClosedError("El servicio de transmision esta cerrado")
            subscription = FrameSubscription()
            self._subscriptions.add(subscription)
            if self._producer is None or self._producer.done():
                self._producer = asyncio.create_task(self._produce(), name="webcam-stream")
            return subscription

    async def unsubscribe(self, subscription: FrameSubscription) -> None:
        async with self._lock:
            self._subscriptions.discard(subscription)
            subscription.fail(StreamClosedError("Suscripcion cerrada"))
            if not self._subscriptions:
                await self._stop_producer()

    async def close(self) -> None:
        async with self._lock:
            self._closed = True
            for subscription in self._subscriptions:
                subscription.fail(StreamClosedError("Servidor cerrando"))
            self._subscriptions.clear()
            await self._stop_producer()

    async def _stop_producer(self) -> None:
        producer, self._producer = self._producer, None
        if producer is not None:
            producer.cancel()
            try:
                await producer
            except asyncio.CancelledError:
                pass

    async def _produce(self) -> None:
        camera_started = False
        try:
            # No bloquear el loop si otra operacion esta liberando la webcam.
            # Completar el arranque antes de detenerlo si llega una cancelacion.
            startup = asyncio.create_task(asyncio.to_thread(self._camera.start))
            try:
                await asyncio.shield(startup)
            except asyncio.CancelledError:
                await startup
                camera_started = True
                raise
            camera_started = True
            previous_id = None
            loop = asyncio.get_running_loop()
            while True:
                started = loop.time()
                try:
                    capture = asyncio.create_task(asyncio.to_thread(
                        self._camera.capture, after_frame_id=previous_id, timeout=1,
                    ))
                    try:
                        frame = await asyncio.shield(capture)
                    except asyncio.CancelledError:
                        # to_thread no cancela la captura sincrona. Esperarla
                        # evita dejar una demanda activa despues de la parada.
                        try:
                            await capture
                        except (CameraError, TimeoutError):
                            pass
                        raise
                except TimeoutError:
                    continue
                previous_id = frame.frame_id
                encoded = await asyncio.to_thread(self._encode, frame)
                packet = StreamPacket(encoded)
                for subscription in self._subscriptions:
                    subscription.offer_preview(packet)
                await asyncio.sleep(max(0, self._interval - (loop.time() - started)))
        except asyncio.CancelledError:
            raise
        except Exception as exc:
            for subscription in self._subscriptions:
                subscription.fail(exc)
        finally:
            if camera_started:
                cleanup = asyncio.create_task(asyncio.to_thread(self._camera.stop))
                try:
                    try:
                        await asyncio.shield(cleanup)
                    except asyncio.CancelledError:
                        # Una desconexion puede llegar cuando el productor ya
                        # estaba cerrando por un fallo de captura. Esperar su
                        # parada tambien en ese caso, sin dejarla huerfana.
                        await cleanup
                        raise
                except Exception as exc:
                    logger.exception("No se pudo detener la webcam del streaming")
                    for subscription in self._subscriptions:
                        subscription.fail(exc)

    def _encode(self, frame: CameraFrame) -> EncodedFrame:
        success, data = cv2.imencode(".jpg", frame.image_bgr, [cv2.IMWRITE_JPEG_QUALITY, self._jpeg_quality])
        if not success:
            raise CameraError("No se pudo codificar el frame como JPEG")
        return EncodedFrame(frame.frame_id, frame.captured_at, frame.width, frame.height, data.tobytes())
