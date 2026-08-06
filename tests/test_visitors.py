import copy
import importlib.util
import sys
import types
import unittest
from pathlib import Path
from unittest.mock import patch


ASSETS = Path(__file__).parents[1] / "be.fri3d.foxhunt" / "assets"
sys.path.insert(0, str(ASSETS))


class _Editor:
    def __init__(self, prefs):
        self.prefs = prefs

    def put_dict(self, key, value):
        self.prefs.data[key] = copy.deepcopy(value)
        return self

    def put_list(self, key, value):
        self.prefs.data[key] = copy.deepcopy(value)
        return self

    def put_dict_item(self, key, item, value):
        self.prefs.data.setdefault(key, {})[item] = copy.deepcopy(value)
        return self

    def commit(self):
        return None


class _Prefs:
    data = {}

    def __init__(self, _name):
        pass

    def get_dict(self, key, default=None):
        return copy.deepcopy(self.data.get(key, default))

    def get_list(self, key, default=None):
        return copy.deepcopy(self.data.get(key, default))

    def edit(self):
        return _Editor(self)


class VisitorTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.clock = [1_786_021_200]
        mpos = types.ModuleType("mpos")
        mpos.__path__ = []
        mpos.SharedPreferences = _Prefs
        mpos_time = types.ModuleType("mpos.time")
        mpos_time.localtime = lambda: (2026, 8, 7, 12, 0, 0, 0, 0)
        mpos_time.epoch_seconds = lambda: cls.clock[0]
        mpos.time = mpos_time

        spec = importlib.util.spec_from_file_location(
            "store_visitor_under_test", ASSETS / "store.py"
        )
        cls.store = importlib.util.module_from_spec(spec)
        with patch.dict(sys.modules, {"mpos": mpos, "mpos.time": mpos_time}):
            spec.loader.exec_module(cls.store)

    def setUp(self):
        _Prefs.data = {
            "profile": {
                "name": "Fien",
                "badge_id": "A4:CF:12:9B:03:7E",
                "hunter_id": None,
                "since": 1_786_021_200,
            },
            "caught": [0],
        }
        self.clock[0] = 1_786_021_200

    def test_schedule_is_seeded_inside_three_spread_out_windows(self):
        start = self.clock[0]
        due = [
            self.store.visitor_due_at(start, "A4:CF:12:9B:03:7E", slot)
            for slot in range(3)
        ]

        self.assertEqual(
            due,
            [
                self.store.visitor_due_at(start, "A4:CF:12:9B:03:7E", slot)
                for slot in range(3)
            ],
        )
        windows = ((2, 4), (18, 26), (38, 48))
        for when, (lo, hi) in zip(due, windows):
            self.assertGreaterEqual(when, start + lo * 60 * 60)
            self.assertLessEqual(when, start + hi * 60 * 60)

    def test_random_visitor_is_unknown_and_always_base_tier(self):
        by_id = {c["id"]: c for c in self.store.CREATURES}
        for slot in range(500):
            cid = self.store.visitor_creature_for("badge-%d" % slot, slot, [0, 1])
            self.assertNotIn(cid, (0, 1))
            self.assertEqual(by_id[cid]["rarity"], "norm")

        all_base = [c["id"] for c in self.store.CREATURES if c["rarity"] == "norm"]
        self.assertIsNone(self.store.visitor_creature_for("badge", 0, all_base))

    def test_due_visit_waits_and_claim_is_reported_once(self):
        due = self.store.visitor_due_at(self.clock[0], "A4:CF:12:9B:03:7E", 0)
        self.clock[0] = due

        cid = self.store.visitor_pending()
        self.assertIsNotNone(cid)
        self.assertEqual(self.store.visitor_pending(), cid)

        claimed = self.store.claim_visitor()
        self.assertEqual(claimed, cid)
        self.assertIn(cid, self.store.caught_ids())
        self.assertEqual(_Prefs.data["origins"][str(cid)], "bezoek")
        self.assertEqual(_Prefs.data["outbox"][0]["kind"], "visitor")
        self.assertEqual(
            _Prefs.data["outbox"][0]["data"], {"slot": 0, "creature_id": cid}
        )
        self.assertIsNone(self.store.claim_visitor())

    def test_social_progress_skips_visit_thresholds(self):
        _Prefs.data["caught"] = [0, 1, 2]
        self.clock[0] += 30 * 60 * 60

        self.assertIsNone(self.store.visitor_pending())
        self.assertEqual(_Prefs.data["visitor"]["slot"], 2)

    def test_debug_meeting_appears_after_ten_seconds_and_stays_local(self):
        due = self.store.schedule_debug_visitor()
        self.assertEqual(due, self.clock[0] + 10)
        self.assertIsNone(self.store.visitor_pending())

        self.clock[0] += 10
        cid = self.store.visitor_pending()
        self.assertIsNotNone(cid)
        self.assertEqual(self.store.claim_visitor(), cid)
        self.assertNotIn("outbox", _Prefs.data)

    def test_hunter_gets_no_new_visit_but_keeps_an_existing_one(self):
        due = self.store.visitor_due_at(self.clock[0], "A4:CF:12:9B:03:7E", 0)
        self.clock[0] = due
        pending = self.store.visitor_pending()
        _Prefs.data["profile"]["hunter_id"] = "JGR-0042"

        self.assertEqual(self.store.visitor_pending(), pending)
        self.store.claim_visitor()
        self.clock[0] += 60 * 60 * 60
        self.assertIsNone(self.store.visitor_pending())


if __name__ == "__main__":
    unittest.main()
