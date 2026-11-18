"""Contrato minimo de lectura del PLC para el monitor de disparos."""

from typing import Protocol


class PLCTriggerSource(Protocol):
    """Lo cumple PLCService y permite sustituirlo por dobles en las pruebas."""

    def esta_conectado(self) -> bool: ...

    def leer_entrada_trigger(self) -> bool | None: ...
