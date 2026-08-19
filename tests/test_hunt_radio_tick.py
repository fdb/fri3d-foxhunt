import types
import unittest
from unittest.mock import MagicMock

from hunt_loader import load_screens_hunt


class HuntRadioTickTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.module, stubs = load_screens_hunt("screens_hunt_radio_tick_under_test")
        cls.radio = stubs["fox_radio"].RADIO

    def setUp(self):
        self.radio.reset_mock()
        self.radio.reading.return_value = types.SimpleNamespace(rssi=-80, link=1)

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


if __name__ == "__main__":
    unittest.main()
