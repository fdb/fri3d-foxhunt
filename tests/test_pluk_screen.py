import importlib.util
import sys
import types
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch


ASSETS = Path(__file__).parents[1] / "be.fri3d.foxhunt" / "assets"
sys.path.insert(0, str(ASSETS))


class PlukScreenTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.store = MagicMock()
        cls.sound = MagicMock()
        # leds.py merged into sound.py: the app's `import sound as leds`
        # resolves both names to one module, so one mock serves both.
        cls.leds = cls.sound

        mpos = types.ModuleType("mpos")
        mpos.Activity = type("Activity", (), {})

        pluk_radio = types.ModuleType("pluk_radio")
        pluk_radio.RADIO = MagicMock()
        pluk_radio.SSID = "fri3d-badge"
        pluk_radio.PLUK_LEVEL = 4
        pluk_radio.yield_for = MagicMock(return_value={"bes": 2, "noot": 0})
        cls.pluk_radio = pluk_radio

        modules = {
            "lvgl": MagicMock(),
            "mpos": mpos,
            "ui": MagicMock(),
            "art": MagicMock(),
            "leds": cls.leds,
            "sound": cls.sound,
            "store": cls.store,
            "pluk_radio": pluk_radio,
        }
        spec = importlib.util.spec_from_file_location(
            "screen_pluk_under_test", ASSETS / "screen_pluk.py"
        )
        cls.module = importlib.util.module_from_spec(spec)
        with patch.dict(sys.modules, modules):
            spec.loader.exec_module(cls.module)

    def setUp(self):
        self.store.reset_mock()
        self.sound.reset_mock()
        self.leds.reset_mock()
        self.pluk_radio.yield_for.reset_mock(return_value=True, side_effect=True)
        self.pluk_radio.yield_for.return_value = {"bes": 2, "noot": 0}

    def test_harvest_uses_camp_phase_and_builds_creature_payoff(self):
        self.store.pluk_phase.return_value = "2026-08-07"
        self.store.record_pluk.return_value = 12  # Knoricorn: legendary
        screen = MagicMock()
        screen._armed = True
        screen._target.bssid = "aa:bb:cc:dd:ee:ff"

        self.module.PlukActivity._pluk(screen)

        self.pluk_radio.yield_for.assert_called_once_with(
            "aa:bb:cc:dd:ee:ff", "2026-08-07"
        )
        self.store.record_pluk.assert_called_once_with(
            "aa:bb:cc:dd:ee:ff", {"bes": 2, "noot": 0}
        )
        self.sound.play.assert_called_once_with("legendary")
        self.leds.off.assert_called_once_with()
        screen._build_oogst.assert_called_once_with({"bes": 2, "noot": 0}, 12)

    def test_harvest_without_creature_keeps_normal_payoff(self):
        self.store.pluk_phase.return_value = "2026-08-07"
        self.store.record_pluk.return_value = None
        screen = MagicMock()
        screen._armed = True
        screen._target.bssid = "aa:bb:cc:dd:ee:ff"

        self.module.PlukActivity._pluk(screen)

        self.sound.play.assert_called_once_with("caught")
        screen._build_oogst.assert_called_once_with({"bes": 2, "noot": 0}, None)


if __name__ == "__main__":
    unittest.main()
