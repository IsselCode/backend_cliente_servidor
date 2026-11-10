from collections import deque
from queue import Queue
from threading import Barrier, Event, Thread, current_thread
import unittest
from unittest.mock import Mock

from core.services.plc_trigger_service import PLCTriggerMonitor


class ScriptedPLC:
    def __init__(self, states=(), *, connected=True, observed_reads=8):
        self.states = deque(states)
        self.state = False
        self.connected = connected
        self.reads = 0
        self.observed_reads = observed_reads
        self.observed = Event()

    def esta_conectado(self):
        return self.connected

    def leer_entrada_trigger(self):
        self.reads += 1
        if self.states:
            self.state = self.states.popleft()
        if self.reads >= self.observed_reads:
            self.observed.set()
        return self.state


class PLCTriggerMonitorTests(unittest.TestCase):
    def monitor(self, plc, **kwargs):
        monitor = PLCTriggerMonitor(plc, interval_ms=1, **kwargs)
        self.addCleanup(monitor.stop, 1)
        return monitor

    def test_creation_is_inactive_and_start_requires_a_consumer(self):
        plc = ScriptedPLC()
        monitor = self.monitor(plc)
        self.assertFalse(monitor.is_running)
        self.assertIsNone(monitor.last_error)
        self.assertEqual(plc.reads, 0)
        with self.assertRaisesRegex(ValueError, "on_trigger"):
            monitor.start()
        self.assertTrue(monitor.stop())

    def test_only_rising_edges_trigger_and_callbacks_use_the_monitor_thread(self):
        plc = ScriptedPLC([False, True, True, False, True])
        threads = []
        monitor = self.monitor(plc, on_trigger=lambda: threads.append(current_thread()))
        self.assertTrue(monitor.start())
        self.assertTrue(plc.observed.wait(1))
        self.assertTrue(monitor.stop(1))
        self.assertEqual(len(threads), 2)
        self.assertTrue(all(thread is not current_thread() for thread in threads))
        self.assertFalse(monitor.is_running)

    def test_initial_high_triggers_once_like_the_original_monitor(self):
        plc = ScriptedPLC([True])
        callback = Mock()
        monitor = self.monitor(plc, on_trigger=callback)
        monitor.start()
        self.assertTrue(plc.observed.wait(1))
        self.assertTrue(monitor.stop(1))
        callback.assert_called_once_with()

    def test_start_can_bind_the_callbacks_of_the_app_state_instance(self):
        plc = ScriptedPLC([True])
        triggered = Event()
        monitor = self.monitor(plc)
        self.assertTrue(monitor.start(on_trigger=triggered.set))
        self.assertTrue(triggered.wait(1))
        self.assertTrue(monitor.stop(1))

    def test_concurrent_starts_create_only_one_execution(self):
        monitor = self.monitor(ScriptedPLC(), on_trigger=Mock())
        barrier = Barrier(6)
        results = Queue()

        def start():
            barrier.wait(timeout=1)
            results.put(monitor.start())

        callers = [Thread(target=start) for _ in range(5)]
        for caller in callers:
            caller.start()
        barrier.wait(timeout=1)
        for caller in callers:
            caller.join(1)
            self.assertFalse(caller.is_alive())
        self.assertEqual(sum(results.get_nowait() for _ in callers), 1)
        self.assertTrue(monitor.stop(1))

    def test_repeated_start_does_not_replace_active_callbacks(self):
        plc = ScriptedPLC([True])
        original = Event()
        replacement = Mock()
        monitor = self.monitor(plc, on_trigger=original.set)
        monitor.start()
        self.assertFalse(monitor.start(on_trigger=replacement))
        self.assertTrue(original.wait(1))
        self.assertTrue(monitor.stop(1))
        replacement.assert_not_called()

    def test_invalid_read_stops_once_instead_of_manufacturing_an_edge(self):
        plc = ScriptedPLC([True, None, True])
        trigger = Mock()
        errors = Queue()
        monitor = self.monitor(plc, on_trigger=trigger, on_error=errors.put_nowait)
        with self.assertLogs("core.services.plc_trigger_service", level="ERROR"):
            monitor.start()
            message = errors.get(timeout=1)
            self.assertTrue(monitor.stop(1))
        self.assertIn("leer", message)
        self.assertEqual(monitor.last_error, message)
        self.assertEqual(trigger.call_count, 1)
        self.assertEqual(list(plc.states), [True])
        self.assertTrue(errors.empty())

    def test_disconnected_plc_reports_error_without_reading(self):
        plc = ScriptedPLC(connected=False)
        trigger = Mock()
        errors = Queue()
        monitor = self.monitor(plc, on_trigger=trigger, on_error=errors.put_nowait)
        with self.assertLogs("core.services.plc_trigger_service", level="ERROR"):
            monitor.start()
            message = errors.get(timeout=1)
            self.assertTrue(monitor.stop(1))
        self.assertIn("no esta conectado", message)
        self.assertEqual(plc.reads, 0)
        trigger.assert_not_called()

    def test_trigger_callback_failure_stops_and_is_reported(self):
        errors = Queue()
        monitor = self.monitor(
            ScriptedPLC([True]),
            on_trigger=Mock(side_effect=RuntimeError("cola llena")),
            on_error=errors.put_nowait,
        )
        with self.assertLogs("core.services.plc_trigger_service", level="ERROR"):
            monitor.start()
            message = errors.get(timeout=1)
            self.assertTrue(monitor.stop(1))
        self.assertIn("on_trigger", message)
        self.assertIn("cola llena", message)
        self.assertEqual(monitor.last_error, message)

    def test_error_callback_failure_does_not_escape_the_thread(self):
        monitor = self.monitor(
            ScriptedPLC(connected=False),
            on_trigger=Mock(),
            on_error=Mock(side_effect=RuntimeError("error al notificar")),
        )
        # on_error avisa antes de lanzar para poder esperar sin carreras con stop.
        entered = Event()

        def failing_callback(message):
            entered.set()
            raise RuntimeError("error al notificar")

        with self.assertLogs("core.services.plc_trigger_service", level="ERROR") as logs:
            monitor.start(on_error=failing_callback)
            self.assertTrue(entered.wait(1))
            self.assertTrue(monitor.stop(1))
        self.assertTrue(any("Fallo en on_error" in record for record in logs.output))
        self.assertIn("no esta conectado", monitor.last_error)

    def test_stop_during_a_read_suppresses_a_late_trigger_and_prevents_duplicates(self):
        entered = Event()
        release = Event()
        trigger = Mock()
        plc = Mock()
        plc.esta_conectado.return_value = True

        def read():
            entered.set()
            if not release.wait(2):
                raise TimeoutError("la prueba no libero la lectura")
            return True

        plc.leer_entrada_trigger.side_effect = read
        monitor = self.monitor(plc, on_trigger=trigger)
        self.addCleanup(release.set)
        monitor.start()
        self.assertTrue(entered.wait(1))
        self.assertFalse(monitor.stop(timeout=0.01))
        self.assertTrue(monitor.is_running)
        self.assertFalse(monitor.start())
        release.set()
        self.assertTrue(monitor.stop(1))
        trigger.assert_not_called()
        self.assertIsNone(monitor.last_error)

    def test_a_callback_can_request_stop_without_joining_itself(self):
        stopped = Queue()
        monitor = self.monitor(ScriptedPLC([True]))
        monitor.start(on_trigger=lambda: stopped.put_nowait(monitor.stop()))
        self.assertFalse(stopped.get(timeout=1))
        self.assertTrue(monitor.stop(1))
        self.assertIsNone(monitor.last_error)

    def test_explicit_restart_after_failure_reuses_callbacks_and_clears_error(self):
        plc = ScriptedPLC([None])
        triggers = Queue()
        errors = Queue()
        monitor = self.monitor(plc, on_trigger=lambda: triggers.put_nowait(True), on_error=errors.put_nowait)
        with self.assertLogs("core.services.plc_trigger_service", level="ERROR"):
            monitor.start()
            errors.get(timeout=1)
            self.assertTrue(monitor.stop(1))
        self.assertIsNotNone(monitor.last_error)
        plc.states.extend([False, True])
        self.assertTrue(monitor.start())
        self.assertTrue(triggers.get(timeout=1))
        self.assertTrue(monitor.stop(1))
        self.assertIsNone(monitor.last_error)

    def test_invalid_intervals_and_callbacks_are_rejected(self):
        for value in (0, -1, float("nan"), float("inf"), True, "20"):
            with self.subTest(interval=value), self.assertRaises(ValueError):
                PLCTriggerMonitor(ScriptedPLC(), interval_ms=value)
        for kwargs in ({"on_trigger": 1}, {"on_error": "error"}):
            with self.subTest(callback=kwargs), self.assertRaises(TypeError):
                PLCTriggerMonitor(ScriptedPLC(), **kwargs)


if __name__ == "__main__":
    unittest.main()
