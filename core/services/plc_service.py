from core.drivers.plc_modbus_driver import PLCModbusDriver


class PLCService:
    # Mapeo de negocio -> direcciones Modbus
    Q1_ADDRESS = 8192
    Q2_ADDRESS = 8193
    Q3_ADDRESS = 8194
    Q4_ADDRESS = 8195
    TRIGGER_INPUT_INDEX = 0

    def __init__(self, driver: PLCModbusDriver):
        self._driver = driver
        self.active_workspace_key: str | None = None
        self.connected_workspace_key: str | None = None
        self.connected_plc_ip: str | None = None

    def conectar(self, ip: str) -> bool:
        ip = ip.strip()
        connected = self._driver.connect(ip)
        self.connected_plc_ip = ip if connected else None
        return connected

    def esta_conectado(self) -> bool:
        return self._driver.is_connected()

    def cerrar(self) -> None:
        self._driver.close()
        self.connected_workspace_key = None
        self.connected_plc_ip = None

    # Internal lifecycle names kept explicit for callers outside the HTTP layer.
    connect = conectar
    close = cerrar

    def activate_workspace(self, workspace_key: str, ip: str) -> bool:
        if self.active_workspace_key != workspace_key:
            self.cerrar()
            self.active_workspace_key = workspace_key
        if self.connected_workspace_key == workspace_key and self.connected_plc_ip == ip and self.esta_conectado():
            return True
        self.cerrar()
        connected = self.conectar(ip)
        if connected:
            self.connected_workspace_key = workspace_key
        return connected

    def status(self, workspace_key: str, configured_ip: str) -> dict:
        return {
            "workspace_key": workspace_key,
            "configured_ip": configured_ip,
            "connected_ip": self.connected_plc_ip if self.connected_workspace_key == workspace_key else None,
            "connected": self.connected_workspace_key == workspace_key and self.esta_conectado(),
        }

    def write_output(self, output_name: str, value: bool) -> bool:
        outputs = {"q1": self.q1, "q2": self.q2, "q3": self.q3, "q4": self.q4}
        if output_name not in outputs:
            return False
        return outputs[output_name](value)

    def q1(self, accion: bool) -> bool:
        return self._driver.write_coil(self.Q1_ADDRESS, accion)

    def q2(self, accion: bool) -> bool:
        return self._driver.write_coil(self.Q2_ADDRESS, accion)

    def q3(self, accion: bool) -> bool:
        return self._driver.write_coil(self.Q3_ADDRESS, accion)

    def q4(self, accion: bool) -> bool:
        return self._driver.write_coil(self.Q4_ADDRESS, accion)

    def leer_entrada_trigger(self) -> bool:
        return self._driver.read_discrete_input(self.TRIGGER_INPUT_INDEX)

    def apagar_todas_las_salidas(self) -> None:
        for address in range(self.Q1_ADDRESS, self.Q4_ADDRESS + 1):
            self._driver.write_coil(address, False)
