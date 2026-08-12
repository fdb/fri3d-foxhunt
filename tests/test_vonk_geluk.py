import importlib.util
import sys
import types
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch


ASSETS = Path(__file__).parents[1] / "com.enigmeta.foxhunt" / "assets"
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

    def test_each_direction_is_independent_and_guaranteed(self):
        self.assertEqual(
            self.store.select_vonk_creature(
                [1], [0], "session", "bb", "aa", receiver_is_hunter=False
            ),
            1,
        )
        self.assertIsNone(
            self.store.select_vonk_creature(
                [0], [0, 1], "session", "aa", "bb", receiver_is_hunter=False
            )
        )

    def test_shareable_roster_applies_self_found_and_endpoint_rules(self):
        roster = [0, 16, 12]
        self.assertEqual(
            self.store.shareable_roster(roster, [12], is_hunter=True), [0, 12]
        )
        self.assertEqual(
            self.store.shareable_roster(roster, [16, 12], is_hunter=True),
            [0, 16, 12],
        )
        self.assertEqual(
            self.store.shareable_roster(roster, [12], is_hunter=False),
            [0, 16],
        )

    def test_legendary_only_lands_with_a_gatherer(self):
        self.assertEqual(
            self.store.select_vonk_creature(
                [12], [], "session", "aa", "bb", receiver_is_hunter=False
            ),
            12,
        )
        self.assertIsNone(
            self.store.select_vonk_creature(
                [12], [], "session", "aa", "bb", receiver_is_hunter=True
            )
        )

    def test_selection_is_stable_for_both_badges(self):
        args = ([16, 17, 18], [0], "shared-session", "aa", "bb", False)
        self.assertEqual(
            self.store.select_vonk_creature(*args),
            self.store.select_vonk_creature(*args),
        )

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
