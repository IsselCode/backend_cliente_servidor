"""Contratos compartidos de captura BGR y codificacion de frames."""

from dataclasses import dataclass
from datetime import datetime
from typing import Protocol

import numpy as np
from numpy.typing import NDArray

FRAME_WIDTH = 1920
FRAME_HEIGHT = 1080


class CameraError(RuntimeError):
    pass


class CameraClosedError(CameraError):
    pass


class CameraDriver(Protocol):
    """El trabajador de captura es el unico propietario del dispositivo."""

    def open(self) -> None: ...

    def read(self) -> NDArray[np.uint8]: ...

    def close(self) -> None: ...


@dataclass(frozen=True, slots=True)
class CameraFrame:
    """Snapshot propio, BGR uint8 de solo lectura, con identidad estable.

    Los consumidores que necesiten modificar pixeles deben copiar image_bgr.
    Mantener este objeto permite publicar luego la imagen exacta inspeccionada.
    """

    frame_id: str
    captured_at: datetime
    image_bgr: NDArray[np.uint8]

    @property
    def width(self) -> int:
        return int(self.image_bgr.shape[1])

    @property
    def height(self) -> int:
        return int(self.image_bgr.shape[0])


@dataclass(frozen=True, slots=True)
class EncodedFrame:
    frame_id: str
    captured_at: datetime
    width: int
    height: int
    jpeg: bytes
