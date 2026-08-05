import importlib.util
import sys
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch


ASSETS = Path(__file__).parents[1] / "be.fri3d.foxhunt" / "assets"
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
        spec = importlib.util.spec_from_file_location("fox_radio_under_test", ASSETS / "fox_radio.py")
        cls.module = importlib.util.module_from_spec(spec)
        with patch.dict(sys.modules, {"lvgl": lv}):
            spec.loader.exec_module(cls.module)

    def setUp(self):
        self.timers.clear()
        self.radio = self.module.FakeFoxRadio()

    def test_submit_is_pending_for_half_a_second(self):
        results = []
        creature = self.module.CREATURES[0]

        returned = self.radio.submit_code(creature["id"], creature["code"], results.append)

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


if __name__ == "__main__":
    unittest.main()
