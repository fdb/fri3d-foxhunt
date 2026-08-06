import importlib.util
import sys
import types
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch


ASSETS = Path(__file__).parents[1] / "be.fri3d.foxhunt" / "assets"
sys.path.insert(0, str(ASSETS))


class VonkGelukTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        mpos = types.ModuleType("mpos")
        mpos.__path__ = []
        mpos.SharedPreferences = MagicMock()
        mpos_time = types.ModuleType("mpos.time")
        mpos_time.localtime = MagicMock(return_value=(2026, 8, 7, 12, 0, 0, 0, 0))
        mpos_time.epoch_seconds = MagicMock(return_value=1_786_100_000)
        mpos.time = mpos_time

        spec = importlib.util.spec_from_file_location(
            "store_vonk_under_test", ASSETS / "store.py"
        )
        cls.store = importlib.util.module_from_spec(spec)
        with patch.dict(sys.modules, {"mpos": mpos, "mpos.time": mpos_time}):
            spec.loader.exec_module(cls.store)

    def test_both_players_receive_new_creatures_or_neither_does(self):
        a_roster = [0, 1]
        b_roster = [2, 3]
        successes = 0

        for session in range(500):
            key = "aa@%08x|bb@peer" % session
            for_a = self.store.roll_vonk_geluk(a_roster, b_roster, key)
            for_b = self.store.roll_vonk_geluk(b_roster, a_roster, key)
            self.assertEqual(for_a is None, for_b is None)
            if for_a is not None:
                successes += 1
                self.assertIn(for_a, b_roster)
                self.assertNotIn(for_a, a_roster)
                self.assertIn(for_b, a_roster)
                self.assertNotIn(for_b, b_roster)

        self.assertGreater(successes, 0)

    def test_no_award_when_only_one_roster_has_something_new(self):
        smaller = [0]
        larger = [0, 1]

        for session in range(100):
            key = "session-%d" % session
            self.assertIsNone(self.store.roll_vonk_geluk(smaller, larger, key))
            self.assertIsNone(self.store.roll_vonk_geluk(larger, smaller, key))

    def test_link_builds_the_same_encounter_key_on_both_badges(self):
        from snuffel_link import BaseLink, Peer

        a = BaseLink()
        a._my_mac, a._session = "aa", "session-a"
        b = BaseLink()
        b._my_mac, b._session = "bb", "session-b"

        seen_by_a = Peer("bb", "B", "", [], "session-b")
        seen_by_b = Peer("aa", "A", "", [], "session-a")
        self.assertEqual(a.encounter_key(seen_by_a), b.encounter_key(seen_by_b))


if __name__ == "__main__":
    unittest.main()
