import importlib.util
import os
from pathlib import Path
import sys
import types
import unittest
from unittest.mock import patch


ASSETS = Path(__file__).parents[1] / "be.fri3d.foxhunt" / "assets"


def load_registrar(radio_chip=None):
    lvgl = types.ModuleType("lvgl")
    mpos = types.ModuleType("mpos")
    mpos.TaskManager = object()
    mpos.LoRaManager = types.SimpleNamespace(radioChip=radio_chip)

    spec = importlib.util.spec_from_file_location(
        "registrar_under_test", ASSETS / "registrar.py"
    )
    module = importlib.util.module_from_spec(spec)
    with patch.dict(sys.modules, {"lvgl": lvgl, "mpos": mpos}):
        spec.loader.exec_module(module)
    return module, mpos


class RadioChip:
    def __init__(self, packet_type):
        self.packet_type = packet_type

    def getPacketType(self):
        if isinstance(self.packet_type, Exception):
            raise self.packet_type
        return self.packet_type


class RegistrarLoRaTest(unittest.TestCase):
    def has_lora(self, registrar, mpos, env=None):
        with (
            patch.dict(sys.modules, {"mpos": mpos}),
            patch.dict(os.environ, env or {}, clear=True),
        ):
            return registrar.has_lora()

    def test_missing_radio_does_not_count_as_an_antenna(self):
        registrar, mpos = load_registrar()
        self.assertFalse(self.has_lora(registrar, mpos))

    def test_constructed_driver_without_a_responding_chip_does_not_count(self):
        for reply in (0xFF, 0xFE, RuntimeError("SPI timeout")):
            with self.subTest(reply=reply):
                registrar, mpos = load_registrar(RadioChip(reply))
                self.assertFalse(self.has_lora(registrar, mpos))

    def test_responding_sx1262_counts_as_a_connected_antenna_kit(self):
        for packet_type in (0, 1):  # GFSK and LoRa are the SX1262's valid replies
            with self.subTest(packet_type=packet_type):
                registrar, mpos = load_registrar(RadioChip(packet_type))
                self.assertTrue(self.has_lora(registrar, mpos))

    def test_desktop_override_is_the_only_radio_free_success_path(self):
        registrar, mpos = load_registrar()
        self.assertTrue(self.has_lora(registrar, mpos, {"FOXHUNT_FAKE_LORA": "1"}))


if __name__ == "__main__":
    unittest.main()
