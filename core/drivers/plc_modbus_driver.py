from threading import RLock

from pymodbus.client import ModbusTcpClient
from pymodbus.exceptions import ConnectionException


class PLCModbusDriver:
    def __init__(self):
        self._cliente = None
        self._lock = RLock()

    def connect(self, ip: str) -> bool:
        with self._lock:
            if self._cliente is not None:
                try:
                    self._cliente.close()
                except Exception:
                    pass
                finally:
                    self._cliente = None

            cliente = ModbusTcpClient(ip)
            if not cliente.connect():
                try:
                    cliente.close()
                except Exception:
                    pass
                return False

            self._cliente = cliente
            return True

    def is_connected(self) -> bool:
        with self._lock:
            if self._cliente is None:
                return False
            try:
                return bool(self._cliente.is_socket_open())
            except Exception:
                return False

    def close(self) -> None:
        with self._lock:
            if self._cliente is None:
                return
            try:
                self._cliente.close()
            except Exception:
                pass
            finally:
                self._cliente = None

    def write_coil(self, address: int, value: bool) -> bool:
        with self._lock:
            if self._cliente is None:
                return False
            try:
                resp = self._cliente.write_coil(address=address, value=value)
                if resp is None:
                    return False
                if hasattr(resp, "isError") and resp.isError():
                    return False
                return True
            except ConnectionException:
                self.close()
                return False
            except Exception:
                return False

    def read_discrete_input(self, index: int) -> bool:
        with self._lock:
            if self._cliente is None:
                return False
            try:
                resp = self._cliente.read_discrete_inputs(index)
                if resp is None:
                    return False
                if hasattr(resp, "isError") and resp.isError():
                    return False

                bits = getattr(resp, "bits", None)
                if not bits or len(bits) < 1:
                    return False
                return bool(bits[0])
            except ConnectionException:
                self.close()
                return False
            except Exception:
                return False
