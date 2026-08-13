import importlib.util
import sys
import unittest
from pathlib import Path
from types import ModuleType
from unittest.mock import MagicMock, patch


ASSETS = Path(__file__).parents[1] / "com.enigmeta.foxhunt" / "assets"
sys.path.insert(0, str(ASSETS))


class FakeTimer:
    def __init__(self, callback, delay, user_data):
        self.callback = callback
        self.delay = delay
        self.user_data = user_data
        self.repeat_count = None

    def set_repeat_count(self, count):
        self.repeat_count = count

    def fire(self):
        self.callback(self)


class FakeTime(ModuleType):
    def __init__(self):
        super().__init__("time")
        self.now = 0

    def ticks_ms(self):
        return self.now

    @staticmethod
    def ticks_diff(left, right):
        return left - right

    @staticmethod
    def ticks_add(value, delta):
        return value + delta

    def advance(self, milliseconds):
        self.now += milliseconds


class FoxRadioTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # Load fox_radio against a tiny deterministic LVGL timer. Tests should
        # prove that submit_code schedules a reply, not depend on a GUI loop.
        cls.timers = []
        lv = MagicMock()

        def timer_create(callback, delay, user_data):
            timer = FakeTimer(callback, delay, user_data)
            cls.timers.append(timer)
            return timer

        lv.timer_create = timer_create
        cls.time = FakeTime()
        spec = importlib.util.spec_from_file_location(
            "fox_radio_under_test", ASSETS / "fox_radio.py"
        )
        cls.module = importlib.util.module_from_spec(spec)
        with patch.dict(sys.modules, {"lvgl": lv}):
            spec.loader.exec_module(cls.module)
        cls.module.time = cls.time

    def setUp(self):
        self.timers.clear()
        self.time.now = 0
        self.module.random.seed(0)
        self.radio = self.module.FakeFoxRadio()

    def test_submit_is_pending_for_half_a_second(self):
        results = []
        creature = self.module.CREATURES[0]

        returned = self.radio.submit_code(
            creature["id"], creature["code"], results.append
        )

        self.assertIsNone(returned)
        self.assertEqual(results, [])
        self.assertEqual(len(self.timers), 1)
        self.assertEqual(self.timers[0].delay, 500)
        self.assertEqual(self.timers[0].repeat_count, 1)

        self.timers[0].fire()
        self.assertEqual(results, ["ok"])

    def test_verdict_is_computed_when_the_reply_arrives(self):
        results = []
        creature = self.module.CREATURES[0]

        self.radio.submit_code(creature["id"], "9999", results.append)
        self.assertEqual(results, [])

        self.timers[0].fire()
        self.assertEqual(results, ["wrong"])

    def test_bpm_is_the_rssi_shifted_into_a_pulse_range(self):
        self.assertEqual(self.module.rssi_to_bpm(-40), 215)
        self.assertEqual(self.module.rssi_to_bpm(-120), 135)

    def test_level_auto_ranges_each_fox_independently(self):
        first = self.radio._level(3, -100)
        self.time.advance(100)
        warmer = self.radio._level(3, -70)

        # The same absolute signal is the first sample in fox 4's own window,
        # so it starts near the middle instead of inheriting fox 3's hot end.
        other_fox = self.radio._level(4, -70)

        self.assertLess(first, warmer)
        self.assertEqual(warmer, 5)
        self.assertEqual(other_fox, first)

    def test_level_window_forgets_old_extremes(self):
        tracker = self.module._LevelTracker()
        baseline = tracker.push(-100)
        self.time.advance(100)
        self.assertEqual(tracker.push(-70), 5)

        self.time.advance(self.module.LEVEL_WINDOW_MS + 1)
        self.assertEqual(tracker.push(-70), baseline)

    def test_reading_reports_bounded_levels_that_rise_with_the_walk(self):
        self.radio.start(3)
        readings = []
        for _ in range(20):
            r = self.radio.reading(3)
            self.assertTrue(self.module.RSSI_FAR <= r.rssi <= self.module.RSSI_NEAR)
            self.assertTrue(0 <= r.level <= 5)
            readings.append(r)
            self.time.advance(100)

        self.assertGreater(readings[-1].rssi, readings[0].rssi)
        self.assertGreater(readings[-1].level, readings[0].level)

    def _verdict(self, fox_id, code):
        results = []
        self.radio.submit_code(fox_id, code, results.append)
        self.timers[-1].fire()
        return results[0]

    def test_an_accepted_code_is_burnt_until_the_session_is_reset(self):
        creature = self.module.CREATURES[0]

        self.assertEqual(self._verdict(creature["id"], creature["code"]), "ok")
        self.assertEqual(self._verdict(creature["id"], creature["code"]), "used")

        # The singleton outlives the app — MicroPythonOS keeps sibling modules
        # in sys.modules across a relaunch — so without an explicit reset the
        # next player at that fox is told AL GEBRUIKT by the previous one's
        # play. ALLES WISSEN and every launch call this.
        self.radio.reset()
        self.assertEqual(self._verdict(creature["id"], creature["code"]), "ok")

    def test_reset_forgets_how_far_the_walk_toward_a_fox_had_got(self):
        self.radio.start(3)
        for _ in range(30):
            self.radio.reading(3)
        walked = self.radio.peek(3).rssi

        self.radio.reset()

        self.assertLess(self.radio.peek(3).rssi, walked)
        # Back to the cold-start reading, not merely lower than a hot one.
        self.assertEqual(
            self.radio.peek(3).rssi, self.module.FakeFoxRadio().peek(3).rssi
        )

    def test_the_interface_carries_reset_so_a_real_radio_cannot_break_on_it(self):
        # Same reason start() is on the base class: the callers below are the
        # app's launch and wipe paths, and a real implementation that simply
        # has no local session to drop must not hand them an AttributeError.
        self.assertIsNone(self.module.FoxRadio().reset())


if __name__ == "__main__":
    unittest.main()
