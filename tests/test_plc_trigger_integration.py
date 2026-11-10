import asyncio
import os
from pathlib import Path
from tempfile import TemporaryDirectory
from threading import current_thread
from types import SimpleNamespace
import unittest
from unittest.mock import AsyncMock, Mock, patch

from pymodbus.exceptions import ConnectionException

from core.app.factory import create_app
from core.app.lifecycle import app_lifespan
from core.drivers.plc_modbus_driver import PLCModbusDriver
from core.services.plc_service import PLCService


class PLCReadContractTests(unittest.TestCase):
    def driver(self, response):
        driver = PLCModbusDriver()
        client = Mock()
        client.read_discrete_inputs.return_value = response
        driver._cliente = client
        return driver, client

    def test_low_and_high_are_valid_booleans(self):
        for value in (False, True):
            with self.subTest(value=value):
                response = SimpleNamespace(bits=[value], isError=lambda: False)
                driver, client = self.driver(response)
                self.assertIs(driver.read_discrete_input(0), value)
                client.read_discrete_inputs.assert_called_once_with(0)

    def test_unreadable_responses_are_none_not_a_low_input(self):
        responses = (
            None,
            SimpleNamespace(isError=lambda: True),
            SimpleNamespace(bits=[], isError=lambda: False),
            SimpleNamespace(isError=lambda: False),
        )
        for response in responses:
            with self.subTest(response=response):
                driver, _ = self.driver(response)
                self.assertIsNone(driver.read_discrete_input(0))
        self.assertIsNone(PLCModbusDriver().read_discrete_input(0))

    def test_connection_exception_returns_none_and_closes_the_client(self):
        driver, client = self.driver(None)
        client.read_discrete_inputs.side_effect = ConnectionException("desconectado")
        self.assertIsNone(driver.read_discrete_input(0))
        client.close.assert_called_once_with()
        self.assertFalse(driver.is_connected())

    def test_other_read_exceptions_are_also_invalid_reads(self):
        driver, client = self.driver(None)
        client.read_discrete_inputs.side_effect = OSError("timeout")
        self.assertIsNone(driver.read_discrete_input(0))

    def test_service_preserves_all_three_states(self):
        driver = Mock()
        service = PLCService(driver)
        for value in (False, True, None):
            driver.read_discrete_input.return_value = value
            self.assertIs(service.leer_entrada_trigger(), value)
        self.assertEqual(driver.read_discrete_input.call_args.args, (0,))


class AppCompositionTests(unittest.TestCase):
    def test_factory_registers_one_inactive_monitor_using_the_shared_plc(self):
        with TemporaryDirectory() as directory:
            with patch.dict(os.environ, {"DATABASE_PATH": str(Path(directory) / "app.db")}):
                with patch("core.app.factory.bootstrap_admin_user"), patch.object(PLCModbusDriver, "connect") as connect:
                    app = create_app()
                    state = app.state.container
                    self.assertIs(state.plc_trigger_monitor._plc, state.plc_service)
                    self.assertFalse(state.plc_trigger_monitor.is_running)
                    self.assertIsNone(state.plc_trigger_monitor.last_error)
                    connect.assert_not_called()


class LifecycleTests(unittest.IsolatedAsyncioTestCase):
    async def test_shutdown_joins_monitor_before_closing_plc_outside_event_loop(self):
        calls = []
        main_thread = current_thread()

        def stop():
            self.assertIsNot(current_thread(), main_thread)
            calls.append("monitor.stop")
            return True

        def close():
            self.assertIsNot(current_thread(), main_thread)
            calls.append("plc.close")

        state = SimpleNamespace(
            mdns_service=SimpleNamespace(start=AsyncMock(), stop=AsyncMock()),
            settings=SimpleNamespace(app_port=8000),
            plc_trigger_monitor=SimpleNamespace(stop=stop),
            plc_service=SimpleNamespace(cerrar=close),
        )
        app = SimpleNamespace(state=SimpleNamespace(container=state))
        async with app_lifespan(app):
            self.assertEqual(calls, [])
            await asyncio.sleep(0)
        self.assertEqual(calls, ["monitor.stop", "plc.close"])
        state.mdns_service.start.assert_awaited_once_with(8000)
        state.mdns_service.stop.assert_awaited_once_with()

    async def test_mdns_is_still_released_if_plc_cleanup_fails(self):
        state = SimpleNamespace(
            mdns_service=SimpleNamespace(start=AsyncMock(), stop=AsyncMock()),
            settings=SimpleNamespace(app_port=8000),
            plc_trigger_monitor=Mock(),
            plc_service=SimpleNamespace(cerrar=Mock(side_effect=RuntimeError("fallo de cierre"))),
        )
        app = SimpleNamespace(state=SimpleNamespace(container=state))
        with self.assertRaisesRegex(RuntimeError, "fallo de cierre"):
            async with app_lifespan(app):
                pass
        state.plc_trigger_monitor.stop.assert_called_once_with()
        state.mdns_service.stop.assert_awaited_once_with()


if __name__ == "__main__":
    unittest.main()
