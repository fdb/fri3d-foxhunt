import importlib.util
from pathlib import Path
import sys
import time
import types
import unittest
from unittest.mock import MagicMock, patch


ASSETS = Path(__file__).parents[1] / "com.enigmeta.foxhunt" / "assets"


class RadioChip:
    def __init__(self, packet_type, wakes_on_begin=True):
        self.packet_type = packet_type
        self.wakes_on_begin = wakes_on_begin
        self.awake = packet_type in (0, 1)
        self.packet_type_calls = 0
        self.begin_calls = 0
        self.SPItransfer = MagicMock()

    def getPacketType(self):
        self.packet_type_calls += 1
        if isinstance(self.packet_type, Exception):
            raise self.packet_type
        return 1 if self.awake else self.packet_type

    def begin(self, **_kwargs):
        self.begin_calls += 1
        if self.wakes_on_begin:
            self.awake = True
        return 0 if self.awake else -1

    def setBlockingCallback(self, _blocking):
        pass

    def setDio2AsRfSwitch(self, _enabled):
        pass

    def getDeviceErrors(self):
        return 0

    def getStatus(self):
        return 0x52 if self.awake else 0x00

    def readRegister(self, _address, data, _length):
        data[0] = 0x14 if self.awake else 0xFF
        data[1] = 0x24 if self.awake else 0xFF


class FakeTimer:
    def __init__(self, callback, delay, _user_data, module_stubs):
        self.callback = callback
        self.delay = delay
        self.repeat_count = None
        self.module_stubs = module_stubs

    def set_repeat_count(self, count):
        self.repeat_count = count

    def fire(self):
        with (
            patch.dict(sys.modules, self.module_stubs),
            patch.object(time, "sleep_ms", MagicMock(), create=True),
            patch.object(time, "ticks_ms", MagicMock(return_value=123), create=True),
        ):
            self.callback(self)


class FakeExpander:
    def __init__(self):
        self.writes = []
        self.released = False

    @property
    def config(self):
        return (self.released, False, False, True, True)

    @config.setter
    def config(self, value):
        self.writes.append(value)
        self.released = bool(value & 0x10)


def load_lora(packet_type, wakes_on_begin=True):
    lvgl = types.ModuleType("lvgl")
    timers = []
    module_stubs = {}
    lvgl.timer_create = lambda callback, delay, data: (
        timers.append(FakeTimer(callback, delay, data, module_stubs)) or timers[-1]
    )

    mpos = types.ModuleType("mpos")
    radio = RadioChip(packet_type, wakes_on_begin)
    expander = FakeExpander()
    task_handler = types.SimpleNamespace(disable=MagicMock(), enable=MagicMock())
    mpos.LoRaManager = types.SimpleNamespace(radioChip=radio)
    mpos.DeviceInfo = types.SimpleNamespace(hardware_id="fri3d_2026")
    mpos.io_expander = expander
    mpos.ui = types.SimpleNamespace(task_handler=task_handler)
    machine = types.ModuleType("machine")
    machine.Pin = MagicMock(OUT=1)
    module_stubs.update({"lvgl": lvgl, "mpos": mpos, "machine": machine})

    spec = importlib.util.spec_from_file_location(
        "lora_presence_under_test", ASSETS / "lora.py"
    )
    module = importlib.util.module_from_spec(spec)
    with (
        patch.dict(sys.modules, module_stubs),
        patch.object(time, "sleep_ms", MagicMock(), create=True),
    ):
        spec.loader.exec_module(module)
    module._test_module_stubs = module_stubs
    return module, timers, radio, expander, task_handler


def fire_all(timers, start=0):
    """Run the finite queue of one-shot LVGL phases created by recovery."""
    i = start
    while i < len(timers):
        timers[i].fire()
        i += 1


class LoRaPresenceTest(unittest.TestCase):
    def test_failed_startup_probe_does_not_reset_shared_board_expander(self):
        for reply in (
            0xFF,
            0xFE,
            RuntimeError("SPI timeout"),
        ):
            with self.subTest(reply=reply):
                lora, timers, radio, expander, task_handler = load_lora(
                    reply, wakes_on_begin=False
                )
                fire_all(timers)

                self.assertFalse(lora.LINK.available)
                self.assertFalse(lora.LINK.ready)
                self.assertEqual(lora.LINK.notice()[0], "Geen LoRa-chip aangesloten")
                self.assertEqual(radio.packet_type_calls, 1)
                self.assertEqual(radio.begin_calls, 0)
                self.assertEqual(expander.writes, [])
                self.assertEqual(timers, [])
                task_handler.disable.assert_not_called()
                task_handler.enable.assert_not_called()

    def test_responding_sx1262_schedules_deferred_configuration(self):
        for packet_type in (0, 1):
            with self.subTest(packet_type=packet_type):
                lora, timers, radio, expander, _ = load_lora(packet_type)
                self.assertTrue(lora.LINK.available)
                self.assertEqual(radio.packet_type_calls, 1)
                self.assertEqual(expander.writes, [])
                self.assertEqual(len(timers), 1)
                self.assertEqual(lora.LINK.notice()[0], "LoRa starten...")

                fire_all(timers)

                self.assertTrue(lora.LINK.ready)
                self.assertIsNone(lora.LINK.notice())

    def test_fitted_is_a_pure_query_that_never_resets(self):
        # The register screen asks "is an antenna fitted?" while it builds;
        # that question must never fire the shared CH32 reset pulse.
        lora, timers, radio, expander, task_handler = load_lora(0xFF)

        with patch.dict(sys.modules, lora._test_module_stubs):
            self.assertFalse(lora.LINK.fitted())

        self.assertEqual(expander.writes, [])
        self.assertEqual(timers, [])
        self.assertEqual(radio.begin_calls, 0)
        task_handler.disable.assert_not_called()

    def test_fitted_sees_a_responding_radio_before_bring_up_finishes(self):
        lora, timers, radio, expander, _ = load_lora(1)
        self.assertTrue(lora.LINK.available)
        self.assertFalse(lora.LINK.ready)

        with patch.dict(sys.modules, lora._test_module_stubs):
            self.assertTrue(lora.LINK.fitted())

        self.assertEqual(expander.writes, [])

    def test_word_jager_retry_starts_recovery_without_blocking(self):
        lora, timers, radio, expander, _ = load_lora(0xFF)

        self.assertEqual(timers, [])
        with patch.dict(sys.modules, lora._test_module_stubs):
            self.assertFalse(lora.LINK.ensure_available())
        # The reset assertion is a quick expander write; all waits, release,
        # initialization and verification remain deferred timer phases.
        self.assertEqual(expander.writes, [0x03])
        self.assertEqual(radio.begin_calls, 0)

        fire_all(timers)
        self.assertTrue(lora.LINK.ready)


if __name__ == "__main__":
    unittest.main()
