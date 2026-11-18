"""Acceso a una webcam local mediante OpenCV, sin ajustes industriales ni Qt."""

import sys

import cv2
import numpy as np
from numpy.typing import NDArray

from core.contracts.camera import CameraError


class WebcamDriver:
    """Usar open/read/close desde el mismo trabajador; no abre al construir."""

    def __init__(self, device_index: int = 0) -> None:
        if isinstance(device_index, bool) or not isinstance(device_index, int) or device_index < 0:
            raise ValueError("device_index debe ser un entero no negativo")
        self._device_index = device_index
        self._capture = None

    def open(self) -> None:
        if self._capture is not None:
            return
        # MSMF puede tardar varios segundos al inicializar algunas webcams.
        # DirectShow evita ese arranque en Windows; CAP_ANY conserva el respaldo
        # para dispositivos sin soporte DirectShow y la seleccion en otros SO.
        backends = (cv2.CAP_DSHOW, cv2.CAP_ANY) if sys.platform == "win32" else (cv2.CAP_ANY,)
        for backend in backends:
            capture = None
            try:
                capture = (
                    cv2.VideoCapture(self._device_index)
                    if backend == cv2.CAP_ANY
                    else cv2.VideoCapture(self._device_index, backend)
                )
                if not capture.isOpened():
                    raise CameraError(f"No se pudo abrir la webcam {self._device_index}")
            except Exception as exc:
                if capture is not None:
                    capture.release()
                if backend != cv2.CAP_ANY and isinstance(exc, (CameraError, cv2.error)):
                    continue
                raise
            self._capture = capture
            return

    def read(self) -> NDArray[np.uint8]:
        if self._capture is None:
            raise CameraError("La webcam no esta abierta")
        success, image = self._capture.read()
        if not success or image is None:
            raise CameraError("No se pudo obtener un frame de la webcam")
        return image

    def close(self) -> None:
        capture, self._capture = self._capture, None
        if capture is not None:
            capture.release()
