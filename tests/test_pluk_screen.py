import unittest
from unittest.mock import MagicMock

from hunt_loader import load_screens_hunt


class PlukScreenTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.module, stubs = load_screens_hunt("screens_hunt_pluk_under_test")
        cls.store = stubs["store"]
        cls.sound = stubs["sound"]
        # leds.py merged into sound.py: the app's `import sound as leds`
        # resolves both names to one module, so one mock serves both.
        cls.leds = cls.sound
        cls.pluk_radio = stubs["pluk_radio"]
        cls.pluk_radio.yield_for = MagicMock(return_value={"bes": 2, "noot": 0})

    def setUp(self):
        self.store.reset_mock()
        self.sound.reset_mock()
        self.leds.reset_mock()
        self.pluk_radio.yield_for.reset_mock(return_value=True, side_effect=True)
        self.pluk_radio.yield_for.return_value = {"bes": 2, "noot": 0}

    def test_harvest_uses_camp_phase_and_builds_creature_payoff(self):
        self.store.pluk_phase.return_value = "2026-08-07"
        self.store.record_pluk.return_value = 0  # Vos: base tier
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
        self.sound.play.assert_called_once_with("caught")
        self.leds.off.assert_called_once_with()
        screen._build_oogst.assert_called_once_with({"bes": 2, "noot": 0}, 0)

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
