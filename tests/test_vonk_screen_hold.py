"""The VONK payoff cannot be dismissed by the handshake's trailing tap."""

import sys
import types
import unittest
import re
from pathlib import Path
from unittest.mock import MagicMock


ASSETS = Path(__file__).parents[1] / "com.enigmeta.foxhunt" / "assets"


class FakeTimer:
    def __init__(self, callback, delay):
        self.callback = callback
        self.delay = delay
        self.deleted = False
        self.repeat_count = None

    def set_repeat_count(self, count):
        self.repeat_count = count

    def fire(self):
        self.callback(self)

    def delete(self):
        self.deleted = True


def load_vonk_activity():
    source = (ASSETS / "screens_hunt.py").read_text()
    start = source.index("class VonkActivity")
    end = source.index("# " + "═" * 25 + " screen_pluk", start)

    timers = []
    lv = MagicMock()
    lv.timer_create.side_effect = lambda callback, delay, _data: (
        timers.append(FakeTimer(callback, delay)) or timers[-1]
    )

    class Activity:
        def onResume(self, _screen):
            pass

        def onPause(self, _screen):
            pass

    namespace = {
        "Activity": Activity,
        "lv": lv,
        "LINK": MagicMock(),
        "ui": MagicMock(GOLD=0xE8B23A),
        "sound": MagicMock(),
        "lazy": MagicMock(),
        "Intent": MagicMock(),
        "_VONK_HOLD_MS": int(
            re.search(r"^_VONK_HOLD_MS = (\d+)$", source, re.MULTILINE).group(1)
        ),
    }
    exec(compile(source[start:end], str(ASSETS / "screens_hunt.py"), "exec"), namespace)
    return namespace["VonkActivity"], timers, namespace


class VonkScreenHoldTest(unittest.TestCase):
    def test_all_exit_paths_stay_locked_for_five_seconds(self):
        activity_class, timers, namespace = load_vonk_activity()
        screen = activity_class()
        screen.timer = None
        screen._hold_timer = None
        screen._can_leave = False
        screen._done_label = MagicMock()
        screen.geluk = 7
        screen.finish = MagicMock()
        screen.startActivity = MagicMock()

        screen.onResume(MagicMock())

        self.assertEqual([timer.delay for timer in timers], [500, 5000])
        self.assertEqual(timers[1].repeat_count, 1)
        screen._done()
        screen._open_beest()
        self.assertTrue(screen.onBackPressed(MagicMock()))
        screen.finish.assert_not_called()
        screen.startActivity.assert_not_called()
        namespace["sound"].play.assert_not_called()

        timers[1].fire()

        screen._done_label.set_text.assert_called_once_with("tik om verder te gaan")
        self.assertFalse(screen.onBackPressed(MagicMock()))
        screen._done()
        screen.finish.assert_called_once_with()

    def test_pause_cancels_both_timers_and_resume_restarts_full_hold(self):
        activity_class, timers, _namespace = load_vonk_activity()
        screen = activity_class()
        screen.timer = None
        screen._hold_timer = None
        screen._can_leave = False
        screen._done_label = MagicMock()

        screen.onResume(MagicMock())
        screen.onPause(MagicMock())

        self.assertTrue(timers[0].deleted)
        self.assertTrue(timers[1].deleted)
        self.assertIsNone(screen.timer)
        self.assertIsNone(screen._hold_timer)

        screen.onResume(MagicMock())
        self.assertEqual([timer.delay for timer in timers], [500, 5000, 500, 5000])


if __name__ == "__main__":
    unittest.main()
