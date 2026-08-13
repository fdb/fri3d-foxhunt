# The two-board scoring split (GAME_DESIGN.md, Scoring): store.hunter_score
# and store.gatherer_score are the badge's local mirror of the server's
# formulas (server/src/lib/scoring.ts) — same values, same dedup rules.
import copy
import importlib.util
import sys
import types
import unittest
from pathlib import Path
from unittest.mock import patch


ASSETS = Path(__file__).parents[1] / "com.enigmeta.foxhunt" / "assets"
sys.path.insert(0, str(ASSETS))

from creatures import CREATURES  # noqa: E402  (pure data, safe to import)


def _first(rarity):
    return next(c["id"] for c in CREATURES if c["rarity"] == rarity)


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


class ScoringTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        mpos = types.ModuleType("mpos")
        mpos.__path__ = []
        mpos.SharedPreferences = _Prefs
        mpos_time = types.ModuleType("mpos.time")
        mpos_time.localtime = lambda: (2026, 8, 7, 12, 0, 0, 0, 0)
        mpos_time.epoch_seconds = lambda: 1_786_100_000
        mpos.time = mpos_time

        spec = importlib.util.spec_from_file_location(
            "store_scoring_under_test", ASSETS / "store.py"
        )
        cls.store = importlib.util.module_from_spec(spec)
        with patch.dict(sys.modules, {"mpos": mpos, "mpos.time": mpos_time}):
            spec.loader.exec_module(cls.store)

    def setUp(self):
        _Prefs.data = {}

    def test_hunter_score_sums_self_found_tiers_and_help_credit(self):
        norm, rare, leg = _first("norm"), _first("rare"), _first("leg")
        _Prefs.data["zelf"] = [norm, rare, leg]
        _Prefs.data["helped"] = ["aa:aa", "bb:bb", "cc:cc"]

        self.assertEqual(self.store.hunter_score(), 100 + 300 + 800 + 3 * 50)

    def test_hunter_score_ignores_owned_but_not_self_found(self):
        norm = _first("norm")
        # Caught through snuffel/pluk/start: ownership alone is score-neutral.
        _Prefs.data["caught"] = [norm, _first("rare")]
        _Prefs.data["zelf"] = [norm]

        self.assertEqual(self.store.hunter_score(), 100)

    def test_record_helped_credits_each_peer_once(self):
        self.assertTrue(self.store.record_helped("aa:aa"))
        self.assertFalse(self.store.record_helped("aa:aa"))
        self.assertTrue(self.store.record_helped("bb:bb"))

        self.assertEqual(sorted(self.store.helped_ids()), ["aa:aa", "bb:bb"])
        self.assertEqual(self.store.hunter_score(), 2 * 50)

    def test_gatherer_score_counts_pluks_meetings_and_best_friends(self):
        ids = [c["id"] for c in CREATURES if c["rarity"] == "norm"][:3]
        finished = self.store.pet.default_state("2026-08-06", "Fri3d Camp", 0)
        finished["bond"] = 100
        _Prefs.data.update(
            {
                "caught": ids,
                "origins": {str(ids[0]): "pluk", str(ids[1]): "pluk"},
                "vrienden": [
                    {"mac": "aa:aa", "naam": "Sam", "code": "H01A000C1", "dag": "d"},
                    {"mac": "bb:bb", "naam": "Noor", "code": "H01A000C1", "dag": "d"},
                    {"mac": "cc:cc", "naam": "Lio", "code": "H01A000C1", "dag": "d"},
                ],
                "beast": {str(ids[0]): finished},
            }
        )

        self.assertEqual(self.store.gatherer_score(), 2 * 50 + 3 * 25 + 1 * 100)

    def test_the_two_scores_never_mix(self):
        # A player with both kinds of progress: each board sees only its own.
        norm = _first("norm")
        other = [c["id"] for c in CREATURES if c["rarity"] == "norm"][1]
        _Prefs.data.update(
            {
                "caught": [norm, other],
                "zelf": [norm],
                "helped": ["aa:aa"],
                "origins": {str(other): "pluk"},
                "vrienden": [
                    {"mac": "aa:aa", "naam": "Sam", "code": "H01A000C1", "dag": "d"}
                ],
            }
        )

        self.assertEqual(self.store.hunter_score(), 100 + 50)
        self.assertEqual(self.store.gatherer_score(), 50 + 25)


if __name__ == "__main__":
    unittest.main()
