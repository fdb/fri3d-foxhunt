import importlib.util
import sys
import types
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch


ASSETS = Path(__file__).parents[1] / "com.enigmeta.foxhunt" / "assets"
sys.path.insert(0, str(ASSETS))


class PlukCreatureTest(unittest.TestCase):
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
            "store_pluk_under_test", ASSETS / "store.py"
        )
        cls.store = importlib.util.module_from_spec(spec)
        with patch.dict(sys.modules, {"mpos": mpos, "mpos.time": mpos_time}):
            spec.loader.exec_module(cls.store)

    def test_camp_phase_changes_at_1500_not_midnight(self):
        phase = self.store._pluk_phase_for

        self.assertEqual(phase((2026, 8, 6, 15)), "2026-08-06")
        self.assertEqual(phase((2026, 8, 7, 0)), "2026-08-06")
        self.assertEqual(phase((2026, 8, 7, 14)), "2026-08-06")
        self.assertEqual(phase((2026, 8, 7, 15)), "2026-08-07")
        self.assertEqual(phase((2026, 8, 9, 14)), "2026-08-08")

    def test_phase_handles_month_and_leap_year_boundaries(self):
        phase = self.store._pluk_phase_for

        self.assertEqual(phase((2026, 3, 1, 8)), "2026-02-28")
        self.assertEqual(phase((2024, 3, 1, 8)), "2024-02-29")
        self.assertEqual(phase((2026, 1, 1, 8)), "2025-12-31")

    def test_roll_is_personal_deterministic_and_never_returns_known_creature(self):
        roll = self.store.pluk_creature_for
        args = ("aa:bb:cc:dd:ee:ff", "01:23:45:67:89:ab", "2026-08-07")

        self.assertEqual(roll(*args, []), roll(*args, []))
        for i in range(2_000):
            found = roll(
                "aa:bb:cc:dd:ee:ff",
                "%012x" % i,
                "2026-08-07",
                list(range(11)),
            )
            self.assertNotIn(found, range(11))

    def test_seeded_population_keeps_legendary_encounters_very_rare(self):
        counts = {"norm": 0, "rare": 0, "leg": 0}
        by_id = {c["id"]: c for c in self.store.CREATURES}
        attempts = 20_000

        for i in range(attempts):
            cid = self.store.pluk_creature_for(
                "aa:bb:cc:dd:ee:ff", "%012x" % i, "2026-08-07", [0]
            )
            if cid is not None:
                counts[by_id[cid]["rarity"]] += 1

        # These are deterministic fixture bounds around the design's effective
        # curve (base 18%, rare 6%, leg 1%, after candidate selection).
        self.assertGreater(counts["norm"], 1_500)
        self.assertLess(counts["norm"], 2_300)
        self.assertGreater(counts["rare"], 200)
        self.assertLess(counts["rare"], 500)
        self.assertGreater(counts["leg"], 10)
        self.assertLess(counts["leg"], 80)

    def test_hourly_reharvest_does_not_reroll_the_phase_creature(self):
        state = {
            "spots": {},
            "phase": "2026-08-07",
            "count": 0,
            "creature_spots": [],
        }
        prefs = MagicMock()
        prefs.edit.return_value.put_dict.return_value.commit.return_value = None

        with (
            patch.object(self.store, "_pluk", return_value=state),
            patch.object(self.store, "_now", return_value=1234),
            patch.object(self.store, "profile", return_value={"badge_id": "badge"}),
            patch.object(self.store, "caught_ids", return_value=[0]),
            patch.object(self.store, "pluk_creature_for", return_value=12) as roll,
            patch.object(self.store, "SharedPreferences", return_value=prefs),
            patch.object(self.store, "add_food") as add_food,
            patch.object(self.store, "add_caught") as add_caught,
            patch.object(self.store, "enqueue_report") as report,
        ):
            first = self.store.record_pluk("AA:BB", {"bes": 2})
            second = self.store.record_pluk("AA:BB", {"bes": 2})

        self.assertEqual(first, 12)
        self.assertIsNone(second)
        roll.assert_called_once()
        self.assertEqual(add_food.call_count, 2)  # food still reloads hourly
        add_caught.assert_called_once_with(12, origin="pluk")
        report.assert_called_once_with(
            "pluk",
            {
                "bssid": "aa:bb",
                "phase": "2026-08-07",
                "creature_id": 12,
            },
        )


if __name__ == "__main__":
    unittest.main()
