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
        def setResult(self, result):
            self.result = result

        def finish(self):
            self.finished = True

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
    fox_radio.rssi_to_bpm = MagicMock()
    fox_radio.bpm_to_level = MagicMock()

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
    def test_missing_profile_reports_state_change_to_router(self):
        module, _timers, store, registrar = load_home()
        store.profile.return_value = None
        home = module.HomeActivity()
        home.finished = False

        home.onResume(MagicMock())

        self.assertEqual(home.result, "unregistered")
        self.assertTrue(home.finished)
        registrar.flush.assert_not_called()

    def test_nearby_cards_keep_roster_order_when_signal_changes(self):
        module, _timers, _store, _registrar = load_home()
        module.CREATURES = [
            {"id": 7},
            {"id": 2},
            {"id": 9},
            {"id": 4},
        ]
        readings = {
            7: types.SimpleNamespace(rssi=-75),
            2: types.SimpleNamespace(rssi=-40),
            9: types.SimpleNamespace(rssi=-100),
            4: types.SimpleNamespace(rssi=-60),
        }
        module.RADIO.peek.side_effect = readings.__getitem__
        module.rssi_to_bpm.side_effect = lambda rssi: rssi + 255
        module.bpm_to_level.side_effect = lambda bpm: bpm // 50

        first = module._nearby_cards({2, 4, 7, 9})
        readings[7].rssi, readings[2].rssi = readings[2].rssi, readings[7].rssi
        second = module._nearby_cards({2, 4, 7, 9})

        self.assertEqual([c["id"] for c, _dots in first], [7, 2, 9, 4])
        self.assertEqual([c["id"] for c, _dots in second], [7, 2, 9, 4])
        self.assertNotEqual([dots for _c, dots in first], [dots for _c, dots in second])

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

    def test_standalone_home_does_not_start_sync_timer(self):
        module, timers, _store, registrar = load_home()
        registrar.server_configured.return_value = False
        home = module.HomeActivity()
        home._sync_timer = None

        home._start_sync_retry()

        self.assertEqual(timers, [])
        self.assertIsNone(home._sync_timer)


if __name__ == "__main__":
    unittest.main()
