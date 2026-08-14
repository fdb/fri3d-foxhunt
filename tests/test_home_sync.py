"""Home keeps retrying the durable report outbox while it stays visible."""

import sys
import types
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch


ASSETS = Path(__file__).parents[1] / "com.enigmeta.foxhunt" / "assets"


class FakeTimer:
    def __init__(self, callback, delay):
        self.callback = callback
        self.delay = delay
        self.deleted = False

    def fire(self):
        self.callback(self)

    def delete(self):
        self.deleted = True


def load_home():
    """Load the real Home section without importing the other merged screens."""
    source = (ASSETS / "screens_system.py").read_text()
    profile_marker = "# " + "═" * 25 + " screen_profile"
    source = source.split(profile_marker, 1)[0]

    timers = []
    lvgl = MagicMock()

    def timer_create(callback, delay, _data):
        timer = FakeTimer(callback, delay)
        timers.append(timer)
        return timer

    lvgl.timer_create = timer_create

    class Activity:
        def onResume(self, _screen):
            pass

        def onPause(self, _screen):
            pass

        def onDestroy(self, _screen):
            pass

    mpos = types.ModuleType("mpos")
    mpos.Activity = Activity
    mpos.Intent = type("Intent", (), {})

    creatures = types.ModuleType("creatures")
    creatures.CREATURES = []

    fox_radio = types.ModuleType("fox_radio")
    fox_radio.RADIO = MagicMock()

    foxhunt = types.ModuleType("foxhunt")
    foxhunt.lazy = MagicMock()

    store = MagicMock()
    store.profile.return_value = {"name": "Sam"}
    registrar = MagicMock()
    stubs = {
        "lvgl": lvgl,
        "mpos": mpos,
        "ui": MagicMock(),
        "art": MagicMock(),
        "companion": MagicMock(),
        "store": store,
        "sound": MagicMock(),
        "creatures": creatures,
        "fox_radio": fox_radio,
        "registrar": registrar,
        "foxhunt": foxhunt,
    }
    module = types.ModuleType("screens_system_home_under_test")
    with patch.dict(sys.modules, stubs):
        exec(
            compile(source, str(ASSETS / "screens_system.py"), "exec"), module.__dict__
        )
    return module, timers, store, registrar


class HomeSyncTest(unittest.TestCase):
    def test_home_retries_sync_periodically_and_stops_when_paused(self):
        module, timers, _store, registrar = load_home()
        home = module.HomeActivity()
        home._fresh = True
        home._sync_timer = None
        home._start_visitor_poll = MagicMock()
        home._start_prewarm = MagicMock()
        home._start_nearby_poll = MagicMock()
        home._stop_visitor_poll = MagicMock()
        home._stop_prewarm = MagicMock()
        home._stop_nearby_poll = MagicMock()

        home.onResume(MagicMock())

        registrar.flush.assert_called_once_with()
        self.assertEqual(len(timers), 1)
        self.assertEqual(timers[0].delay, module._SYNC_RETRY_MS)

        timers[0].fire()
        self.assertEqual(registrar.flush.call_count, 2)

        home.onPause(MagicMock())
        self.assertTrue(timers[0].deleted)
        self.assertIsNone(home._sync_timer)


if __name__ == "__main__":
    unittest.main()
