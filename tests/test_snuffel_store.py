import copy
import importlib.util
import sys
import types
import unittest
from pathlib import Path
from unittest.mock import patch


ASSETS = Path(__file__).parents[1] / "com.enigmeta.foxhunt" / "assets"
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


class SnuffelStoreTest(unittest.TestCase):
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
            "store_snuffel_under_test", ASSETS / "store.py"
        )
        cls.store = importlib.util.module_from_spec(spec)
        with patch.dict(sys.modules, {"mpos": mpos, "mpos.time": mpos_time}):
            spec.loader.exec_module(cls.store)

    def setUp(self):
        _Prefs.data = {"voorraad": {"bes": 0, "noot": 0, "eikel": 0}}

    def test_repeat_snuffel_refreshes_friend_name_and_companion(self):
        mac = "aa:bb:cc:dd:ee:ff"
        first = self.store.record_snuffel(mac, "Oude naam", "H01A000C1")
        second = self.store.record_snuffel(mac, "Nieuwe naam", "H02A005C3")

        self.assertTrue(first["new_friend"])
        self.assertFalse(second["new_friend"])
        self.assertEqual(
            self.store.vrienden(),
            [
                {
                    "mac": mac,
                    "naam": "Nieuwe naam",
                    "code": "H02A005C3",
                    "dag": "2026-08-07",
                }
            ],
        )

    def test_food_rearms_after_one_hour_and_spark_after_six(self):
        mac = "aa:bb:cc:dd:ee:ff"
        start = 1_786_100_000
        with patch.object(self.store, "_now", return_value=start):
            first = self.store.record_snuffel(mac, "Sam", "H01A000C1")
        with patch.object(self.store, "_now", return_value=start + 60 * 60):
            food_only = self.store.record_snuffel(mac, "Sam", "H01A000C1")
        with patch.object(self.store, "_now", return_value=start + 6 * 60 * 60):
            next_spark = self.store.record_snuffel(mac, "Sam", "H01A000C1")

        self.assertTrue(first["vonk"])
        self.assertFalse(food_only["vonk"])
        self.assertEqual(food_only["amount"], 1)
        self.assertTrue(next_spark["vonk"])
        self.assertGreaterEqual(next_spark["amount"], 2)

    def test_self_find_date_is_separate_from_received_date(self):
        _Prefs.data.update(
            {
                "caught": [16],
                "beast": {
                    "16": self.store.pet.default_state(
                        "2026-08-06", "Fri3d Camp", 1_786_000_000
                    )
                },
            }
        )

        self.store.zelf_gevonden(16)

        self.assertEqual(self.store.zelf_date(16), "2026-08-07")
        self.assertEqual(_Prefs.data["beast"]["16"]["date"], "2026-08-06")

    def test_restore_preserves_acquisition_and_self_find_dates(self):
        self.store.restore_caught(
            [16],
            [16],
            {"16": "2026-08-06"},
            {"16": "2026-08-08"},
        )

        self.assertEqual(_Prefs.data["beast"]["16"]["date"], "2026-08-06")
        self.assertEqual(self.store.zelf_date(16), "2026-08-08")


if __name__ == "__main__":
    unittest.main()
