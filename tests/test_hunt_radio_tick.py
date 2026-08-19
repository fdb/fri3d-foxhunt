import types
import unittest
from unittest.mock import MagicMock

from hunt_loader import load_screens_hunt


class HuntRadioTickTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.module, stubs = load_screens_hunt("screens_hunt_radio_tick_under_test")
        cls.radio = stubs["fox_radio"].RADIO
        cls.absolute_level = stubs["fox_radio"].bpm_to_level

    def setUp(self):
        self.radio.reset_mock()
        self.absolute_level.reset_mock()
        self.radio.reading.return_value = types.SimpleNamespace(rssi=-80, link=1)
        self.radio.direction_level.return_value = 4

    def test_unchanged_bpm_does_not_invalidate_the_label_again(self):
        screen = MagicMock()
        screen.has_foreground.return_value = True
        screen._bpm_text = None
        screen._beat = False
        screen._bpm_live = True
        screen._mirror_level = 0
        screen.mirror = []

        self.module.HuntActivity._tick(screen, None)
        self.module.HuntActivity._tick(screen, None)

        screen.bpm.set_text.assert_called_once_with("60")
        self.assertEqual(screen.heart.align.call_count, 2)
        self.assertEqual(self.radio.poll.call_count, 2)

    def test_receiver_feedback_budget_is_at_least_five_hz(self):
        self.assertLessEqual(self.module.HUNT_TICK_MS, 200)

    def test_hunt_bars_use_relative_direction_level(self):
        screen = MagicMock()
        screen.has_foreground.return_value = True
        screen._bpm_text = None
        screen._beat = False
        screen._bpm_live = True
        screen._mirror_level = 4
        screen.mirror = []

        self.module.HuntActivity._tick(screen, None)

        self.radio.direction_level.assert_called_once_with(screen.fox_id, -80)
        self.absolute_level.assert_not_called()
        self.module.leds.show_level.assert_called_once_with(4)


if __name__ == "__main__":
    unittest.main()
