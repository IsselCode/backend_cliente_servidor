"""Captura bajo demanda: una webcam, un trabajador y el ultimo frame en memoria."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from math import isfinite
from threading import Condition, Event, RLock, Thread, current_thread
from time import monotonic
from uuid import uuid4

import cv2
import numpy as np

from core.contracts.camera import (
    FRAME_HEIGHT, FRAME_WIDTH, CameraClosedError, CameraDriver, CameraError, CameraFrame,
)


@dataclass(slots=True)
class _CaptureRun:
    stop: Event = field(default_factory=Event)
    thread: Thread | None = None
    latest: CameraFrame | None = None
    latest_started_at: float = 0.0
    error: CameraError | None = None
    finished: bool = False


class CameraService:
    """Construir no conecta hardware. start()/stop() controlan la captura continua.

    capture() tambien funciona sin streaming: arranca temporalmente la camara
    y espera un frame nuevo. Las capturas pendientes retrasan stop(), mientras
    close() solicita el cierre definitivo. Solo el trabajador accede al driver
    y cada imagen reemplaza al ultimo snapshot de solo lectura.
    """

    def __init__(self, driver: CameraDriver, *, capture_fps: float = 30, stop_timeout: float = 5) -> None:
        for name, value in (("capture_fps", capture_fps), ("stop_timeout", stop_timeout)):
            if not isfinite(value) or value <= 0:
                raise ValueError(f"{name} debe ser positivo y finito")
        self._driver = driver
        self._interval = 1 / capture_fps
        self._stop_timeout = stop_timeout
        self._lifecycle_lock = RLock()
        self._condition = Condition()
        self._continuous = False
        self._keep_running = False
        self._pending_captures = 0
        self._run: _CaptureRun | None = None
        self._closed = False
        self._identity = uuid4().hex
        self._sequence = 0

    def start(self) -> None:
        """Mantiene la captura activa hasta stop(); las llamadas son idempotentes."""
        with self._lifecycle_lock, self._condition:
            self._start_run()
            self._continuous = True

    def stop(self) -> None:
        """Detiene la captura continua cuando terminan las capturas pendientes."""
        with self._lifecycle_lock:
            with self._condition:
                self._continuous = False
                run = self._run if not self._keep_running and not self._pending_captures else None
            self._stop_run(run)

    def set_keep_running(self, enabled: bool) -> None:
        """Mantiene la webcam abierta independientemente de la vista previa."""
        with self._lifecycle_lock:
            with self._condition:
                if enabled:
                    self._start_run()
                    self._keep_running = True
                    return
                if not self._keep_running:
                    return
                self._keep_running = False
                run = self._run if not self._continuous and not self._pending_captures else None
            self._stop_run(run)

    def capture(
        self, *, after_frame_id: str | None = None, timeout: float = 2.0,
        not_before: float | None = None, discard_frames: int = 0,
    ) -> CameraFrame:
        """Entrega un frame valido; si estaba detenida, espera una imagen nueva.

        Con la camara activa devuelve el ultimo frame, o espera uno posterior
        a after_frame_id. Sin captura continua libera el dispositivo al terminar
        la ultima captura individual, incluso si falla o vence su timeout.
        not_before usa el reloj monotonic() y exige una lectura iniciada despues
        de ese instante. discard_frames omite snapshots nuevos elegibles antes
        de devolver uno; ambos criterios se aplican dentro del mismo plazo.
        """
        if not isfinite(timeout) or timeout <= 0:
            raise ValueError("timeout debe ser positivo y finito")
        if not_before is not None and not isfinite(not_before):
            raise ValueError("not_before debe ser finito")
        if isinstance(discard_frames, bool) or not isinstance(discard_frames, int) or discard_frames < 0:
            raise ValueError("discard_frames debe ser un entero no negativo")
        with self._lifecycle_lock, self._condition:
            run = self._start_run()
            self._pending_captures += 1
        try:
            return self._wait_for_frame(run, after_frame_id, timeout, not_before, discard_frames)
        finally:
            with self._lifecycle_lock:
                with self._condition:
                    self._pending_captures -= 1
                    stop = (
                        not self._closed and not self._continuous
                        and not self._keep_running and not self._pending_captures
                    )
                if stop:
                    self._stop_run(run)

    def close(self) -> None:
        """Cierre definitivo. Llamar fuera del event loop; intenta un join acotado.

        OpenCV no permite cancelar de forma portable una lectura nativa atascada.
        Si vence el plazo se informa el fallo, sin liberar el driver en paralelo.
        """
        with self._lifecycle_lock:
            with self._condition:
                self._closed = True
                self._continuous = False
                run = self._run
            self._stop_run(run)

    def _start_run(self) -> _CaptureRun:
        # El llamador conserva ambos locks para serializar arranque y parada.
        if self._closed:
            raise CameraClosedError("El servicio de camara esta cerrado")
        run = self._run
        if run is not None and (run.stop.is_set() or run.finished or run.error is not None):
            if self._continuous or self._pending_captures or (run.thread is not None and run.thread.is_alive()):
                raise run.error or CameraError("La captura anterior esta terminando")
            run = None
        if run is None:
            run = _CaptureRun()
            thread = Thread(target=self._capture_loop, args=(run,), name="webcam-capture", daemon=True)
            run.thread = thread
            self._run = run
            try:
                thread.start()
            except Exception:
                self._run = None
                raise
        return run

    def _stop_run(self, run: _CaptureRun | None) -> None:
        if run is None:
            return
        with self._condition:
            run.stop.set()
            self._condition.notify_all()
        thread = run.thread
        if thread is not None:
            if thread is current_thread():
                raise CameraError("No se puede esperar el cierre desde el trabajador de captura")
            thread.join(self._stop_timeout)
            if thread.is_alive():
                raise CameraError("La webcam no termino su lectura dentro del plazo de cierre")
        # Conserva el ultimo frame hasta el siguiente arranque. La nueva
        # ejecucion empieza sin snapshot para no entregar una imagen anterior.

    def _wait_for_frame(
        self, run: _CaptureRun, after_frame_id: str | None, timeout: float,
        not_before: float | None = None, discard_frames: int = 0,
    ) -> CameraFrame:
        deadline = monotonic() + timeout
        last_seen_id = None
        with self._condition:
            while True:
                if self._closed or run.stop.is_set():
                    raise CameraClosedError("El servicio de camara esta cerrado")
                if run.error is not None:
                    raise run.error
                if (
                    run.latest is not None and run.latest.frame_id != after_frame_id
                    and (not_before is None or run.latest_started_at >= not_before)
                    and run.latest.frame_id != last_seen_id
                ):
                    last_seen_id = run.latest.frame_id
                    if discard_frames == 0:
                        return run.latest
                    discard_frames -= 1
                if run.finished:
                    raise CameraError("La captura termino sin un frame disponible")
                remaining = deadline - monotonic()
                if remaining <= 0:
                    raise TimeoutError("No llego un frame nuevo dentro del plazo de captura")
                self._condition.wait(remaining)

    def _capture_loop(self, run: _CaptureRun) -> None:
        try:
            self._driver.open()
            while not run.stop.is_set():
                started = monotonic()
                image = self._driver.read()
                captured_at = datetime.now(timezone.utc)
                if (
                    not isinstance(image, np.ndarray) or image.dtype != np.uint8
                    or image.ndim != 3 or image.shape[2] != 3 or not image.size
                ):
                    raise CameraError("La webcam debe entregar una imagen BGR uint8 no vacia")
                if image.shape[:2] != (FRAME_HEIGHT, FRAME_WIDTH):
                    image = cv2.resize(image, (FRAME_WIDTH, FRAME_HEIGHT), interpolation=cv2.INTER_LINEAR)
                else:
                    image = image.copy()
                image.setflags(write=False)
                with self._condition:
                    if run.stop.is_set():
                        break
                    self._sequence += 1
                    run.latest = CameraFrame(f"{self._identity}:{self._sequence}", captured_at, image)
                    run.latest_started_at = started
                    self._condition.notify_all()
                run.stop.wait(max(0, self._interval - (monotonic() - started)))
        except Exception as exc:
            with self._condition:
                run.error = exc if isinstance(exc, CameraError) else CameraError(str(exc) or type(exc).__name__)
                self._condition.notify_all()
        finally:
            try:
                self._driver.close()
            except Exception as exc:
                with self._condition:
                    if run.error is None:
                        run.error = CameraError(f"Fallo al cerrar la webcam: {exc}")
            finally:
                with self._condition:
                    run.finished = True
                    self._condition.notify_all()
