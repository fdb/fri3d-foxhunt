import importlib.util
from pathlib import Path
import sys
import types
import unittest
from unittest.mock import MagicMock, patch


ASSETS = Path(__file__).parents[1] / "com.enigmeta.foxhunt" / "assets"


class RadioChip:
    def __init__(self, packet_type):
        self.packet_type = packet_type
        self.SPItransfer = MagicMock()

    def getPacketType(self):
        if isinstance(self.packet_type, Exception):
            raise self.packet_type
        return self.packet_type


def load_lora(packet_type):
    lvgl = types.ModuleType("lvgl")
    lvgl.timer_create = MagicMock()

    mpos = types.ModuleType("mpos")
    mpos.LoRaManager = types.SimpleNamespace(radioChip=RadioChip(packet_type))
    mpos.DeviceInfo = types.SimpleNamespace(hardware_id="fri3d_2026")

    spec = importlib.util.spec_from_file_location(
        "lora_presence_under_test", ASSETS / "lora.py"
    )
    module = importlib.util.module_from_spec(spec)
    with patch.dict(sys.modules, {"lvgl": lvgl, "mpos": mpos}):
        spec.loader.exec_module(module)
    return module, lvgl


class LoRaPresenceTest(unittest.TestCase):
    def test_constructed_driver_on_an_open_bus_is_not_available(self):
        for reply in (0xFF, 0xFE, RuntimeError("SPI timeout")):
            with self.subTest(reply=reply):
                lora, lvgl = load_lora(reply)
                self.assertFalse(lora.LINK.available)
                lvgl.timer_create.assert_not_called()

    def test_responding_sx1262_schedules_deferred_configuration(self):
        for packet_type in (0, 1):
            with self.subTest(packet_type=packet_type):
                lora, lvgl = load_lora(packet_type)
                self.assertTrue(lora.LINK.available)
                lvgl.timer_create.assert_called_once()


if __name__ == "__main__":
    unittest.main()
