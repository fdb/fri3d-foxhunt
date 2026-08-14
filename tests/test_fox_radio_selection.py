import importlib.util
from pathlib import Path
import sys
import types
import unittest
from unittest.mock import MagicMock, patch


ASSETS = Path(__file__).parents[1] / "com.enigmeta.foxhunt" / "assets"
sys.path.insert(0, str(ASSETS))


def load_fox_radio(is_fri3d, available):
    lvgl = types.ModuleType("lvgl")
    lvgl.timer_create = MagicMock()
    lora = types.ModuleType("lora")
    lora.LINK = types.SimpleNamespace(
        is_fri3d=is_fri3d,
        available=available,
        active_chars=lambda: [],
        notice=lambda: ("Wachten op LoRa", "controle wordt gestart"),
    )
    lora.LQ_PERIOD_MS = 300
    lora.LQ_WINDOW_MS = 1500

    spec = importlib.util.spec_from_file_location(
        "fox_radio_selection_under_test", ASSETS / "fox_radio.py"
    )
    module = importlib.util.module_from_spec(spec)
    with patch.dict(sys.modules, {"lvgl": lvgl, "lora": lora}):
        spec.loader.exec_module(module)
    return module


class FoxRadioSelectionTest(unittest.TestCase):
    def test_badge_without_a_responding_radio_never_uses_simulated_messages(self):
        fox_radio = load_fox_radio(is_fri3d=True, available=False)

        self.assertIsInstance(fox_radio.RADIO, fox_radio.LoraFoxRadio)
        self.assertEqual(fox_radio.RADIO.active_foxes(), [])
        self.assertEqual(fox_radio.RADIO.notice()[0], "Wachten op LoRa")

    def test_desktop_keeps_the_simulator(self):
        fox_radio = load_fox_radio(is_fri3d=False, available=False)

        self.assertIsInstance(fox_radio.RADIO, fox_radio.FakeFoxRadio)
        self.assertIsNone(fox_radio.RADIO.notice())


if __name__ == "__main__":
    unittest.main()
