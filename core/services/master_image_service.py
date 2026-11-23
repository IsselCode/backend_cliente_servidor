"""Captura iluminada y guardado automatico de la imagen maestra de un workspace."""

from dataclasses import dataclass
import logging
from math import isfinite
from threading import Lock
from time import monotonic

import cv2

from core.contracts.camera import CameraError, CameraFrame
from core.database.repositories.master_config_repository import MasterConfigRepository
from core.errors.exceptions import (
    ConflictError, MasterImageEncodingError, MasterImageError,
    MasterImageLightingError, MasterImageTimeoutError,
)
from core.services.camera_service import CameraService
from core.services.plc_service import PLCService

logger = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class CapturedMasterImage:
    frame: CameraFrame
    png: bytes


class MasterImageService:
    """Reutiliza el PLC y la camara; construir no inicia hardware ni trabajadores.

    La exclusion solo cubre capturas maestras de esta instancia. Los bloqueos
    generales de configuracion y el escalado se describen en docs/.
    """

    def __init__(
        self, plc: PLCService, camera: CameraService, *,
        light_settle_time: float = 0.25, capture_timeout: float = 5,
        discard_frames: int = 2,
    ) -> None:
        if not isfinite(light_settle_time) or light_settle_time < 0:
            raise ValueError("light_settle_time debe ser no negativo y finito")
        if not isfinite(capture_timeout) or capture_timeout <= light_settle_time:
            raise ValueError("capture_timeout debe ser finito y mayor que light_settle_time")
        if isinstance(discard_frames, bool) or not isinstance(discard_frames, int) or discard_frames < 0:
            raise ValueError("discard_frames debe ser un entero no negativo")
        self._plc = plc
        self._camera = camera
        self._light_settle_time = light_settle_time
        self._capture_timeout = capture_timeout
        self._discard_frames = discard_frames
        self._capture_lock = Lock()

    def capture_and_save(
        self, repository: MasterConfigRepository, *, workspace_key: str, configured_ip: str,
    ) -> CapturedMasterImage:
        """Llamar fuera del event loop. Solo guarda tras capturar y apagar Q1."""
        if not self._capture_lock.acquire(blocking=False):
            raise ConflictError("Ya hay una captura de imagen maestra en curso")
        try:
            status = self._plc.status(workspace_key, configured_ip)
            if not status["connected"] or status["connected_ip"] != configured_ip.strip():
                raise MasterImageError("El PLC debe estar conectado al workspace y a su IP configurada")
            frame = self._capture_illuminated_frame()
            try:
                success, encoded = cv2.imencode(".png", frame.image_bgr)
            except cv2.error as exc:
                raise MasterImageEncodingError() from exc
            if not success or encoded is None or not encoded.size:
                raise MasterImageEncodingError()
            png = encoded.tobytes()
            repository.save_master_image(png)
            return CapturedMasterImage(frame, png)
        finally:
            self._capture_lock.release()

    def _capture_illuminated_frame(self) -> CameraFrame:
        try:
            self._set_light(True)
            try:
                return self._camera.capture(
                    not_before=monotonic() + self._light_settle_time,
                    discard_frames=self._discard_frames,
                    timeout=self._capture_timeout,
                )
            except TimeoutError as exc:
                raise MasterImageTimeoutError() from exc
            except CameraError as exc:
                raise MasterImageError(f"Fallo de camara: {exc}") from exc
        finally:
            # Tambien tras un encendido fallido: el PLC pudo recibir la orden
            # aunque su respuesta se haya perdido. No guardar si falla el OFF.
            try:
                self._set_light(False)
            except MasterImageLightingError:
                logger.exception("No se pudo confirmar el apagado de Q1 tras la captura maestra")
                raise

    def _set_light(self, value: bool) -> None:
        action = "encender" if value else "apagar"
        error_detail = f"No se pudo confirmar la orden para {action} Q1 en el PLC"
        try:
            success = self._plc.q1(value)
        except Exception as exc:
            raise MasterImageLightingError(error_detail) from exc
        if not success:
            raise MasterImageLightingError(error_detail)
