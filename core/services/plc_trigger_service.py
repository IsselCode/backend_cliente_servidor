"""Polling del trigger del PLC, independiente de Qt y de la inferencia."""

import logging
from collections.abc import Callable
from math import isfinite
from threading import Event, Lock, Thread, current_thread
from core.contracts.plc import PLCTriggerSource


logger = logging.getLogger(__name__)


class PLCTriggerMonitor:
    """Detecta flancos 0 -> 1 en un hilo y entrega avisos mediante callbacks.

    Los callbacks se ejecutan en el hilo del monitor y deben terminar rapido.
    Una lectura fallida o una excepcion del callback detiene esta ejecucion.
    Crear el objeto no abre conexiones ni inicia el polling.
    """

    def __init__(
        self,
        plc_service: PLCTriggerSource,
        *,
        interval_ms: float = 20,
        on_trigger: Callable[[], None] | None = None,
        on_error: Callable[[str], None] | None = None,
    ) -> None:
        if (
            isinstance(interval_ms, bool)
            or not isinstance(interval_ms, (int, float))
            or not isfinite(interval_ms)
            or interval_ms <= 0
        ):
            raise ValueError("interval_ms debe ser un numero finito mayor que cero")
        self._validate_callbacks(on_trigger, on_error)
        self._plc = plc_service
        self._interval_seconds = interval_ms / 1000
        self._on_trigger = on_trigger
        self._on_error = on_error
        self._lock = Lock()
        self._thread: Thread | None = None
        self._stop_event: Event | None = None
        self._last_error: str | None = None

    @staticmethod
    def _validate_callbacks(
        on_trigger: Callable[[], None] | None,
        on_error: Callable[[str], None] | None,
    ) -> None:
        if on_trigger is not None and not callable(on_trigger):
            raise TypeError("on_trigger debe ser una funcion")
        if on_error is not None and not callable(on_error):
            raise TypeError("on_error debe ser una funcion")

    @property
    def is_running(self) -> bool:
        """Sigue siendo True mientras una parada espera una lectura en curso."""
        with self._lock:
            return self._thread is not None and self._thread.is_alive()

    @property
    def last_error(self) -> str | None:
        with self._lock:
            return self._last_error

    def start(
        self,
        *,
        on_trigger: Callable[[], None] | None = None,
        on_error: Callable[[str], None] | None = None,
    ) -> bool:
        """Inicia una ejecucion; devuelve False si el hilo anterior sigue vivo.

        Se pueden proporcionar callbacks al construir el monitor o al arrancar
        el que vive en AppState. Un start repetido no cambia los callbacks de
        una ejecucion activa. Se requiere on_trigger para no perder avisos.
        """
        self._validate_callbacks(on_trigger, on_error)
        with self._lock:
            if self._thread is not None and self._thread.is_alive():
                return False
            trigger_callback = on_trigger if on_trigger is not None else self._on_trigger
            error_callback = on_error if on_error is not None else self._on_error
            if trigger_callback is None:
                raise ValueError("Configura on_trigger antes de iniciar el monitor")

            stop_event = Event()
            thread = Thread(
                target=self._run,
                args=(stop_event, trigger_callback, error_callback),
                name="plc-trigger-monitor",
                daemon=True,
            )
            self._on_trigger = trigger_callback
            self._on_error = error_callback
            self._last_error = None
            self._stop_event = stop_event
            self._thread = thread
            try:
                thread.start()
            except Exception:
                self._thread = None
                self._stop_event = None
                raise
            return True

    def stop(self, timeout: float | None = None) -> bool:
        """Solicita la parada y espera la lectura/callback en curso.

        Sin timeout espera hasta terminar. Devuelve False si vence el timeout
        o si se llama desde un callback: en ese caso solicita la parada, pero
        no intenta hacer join del propio hilo. No cierra la conexion al PLC.
        """
        with self._lock:
            thread = self._thread
            if thread is None:
                return True
            assert self._stop_event is not None
            self._stop_event.set()

        if thread is current_thread():
            return False
        thread.join(timeout)
        return not thread.is_alive()

    def _run(
        self,
        stop_event: Event,
        on_trigger: Callable[[], None],
        on_error: Callable[[str], None] | None,
    ) -> None:
        # Conserva el comportamiento original: una primera lectura alta dispara.
        previous_state = False
        try:
            while not stop_event.is_set():
                if not self._plc.esta_conectado():
                    raise ConnectionError("El PLC no esta conectado")
                state = self._plc.leer_entrada_trigger()
                # Una parada durante la lectura no debe producir un aviso tardio.
                if stop_event.is_set():
                    break
                if not isinstance(state, bool):
                    raise ConnectionError("No se pudo leer la entrada de trigger del PLC")

                if state and not previous_state:
                    try:
                        on_trigger()
                    except Exception as exc:
                        detail = str(exc) or type(exc).__name__
                        raise RuntimeError(f"Fallo en on_trigger: {detail}") from exc
                previous_state = state

                # Event.wait permite despertar inmediatamente al solicitar stop.
                if stop_event.wait(self._interval_seconds):
                    break
        except Exception as exc:
            if not stop_event.is_set():
                message = str(exc) or type(exc).__name__
                with self._lock:
                    self._last_error = message
                logger.error("Monitor de trigger detenido: %s", message)
                if on_error is not None:
                    try:
                        on_error(message)
                    except Exception:
                        logger.exception("Fallo en on_error del monitor de trigger")
        finally:
            stop_event.set()
