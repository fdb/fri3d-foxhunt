import importlib.util
import sys
import types
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch


ASSETS = Path(__file__).parents[1] / "com.enigmeta.foxhunt" / "assets"


class _Editor:
    def __init__(self, prefs):
        self.prefs = prefs

    def put_dict(self, key, value):
        self.prefs.data[key] = value
        return self

    def commit(self):
        type(self.prefs).commits += 1
        return True


class _Prefs:
    data = {}
    commits = 0

    def __init__(self, _app):
        pass

    def get_dict(self, key, default=None):
        if key in self.data:
            # Match SharedPreferences: malformed scalar values fail while it
            # tries to return a defensive dict copy.
            return dict(self.data[key])
        return default

    def edit(self):
        return _Editor(self)


def load_store():
    mpos = types.ModuleType("mpos")
    mpos.__path__ = []
    mpos.SharedPreferences = _Prefs
    mpos_time = types.ModuleType("mpos.time")
    mpos_time.epoch_seconds = MagicMock(return_value=1_786_715_176)
    mpos_time.localtime = MagicMock(return_value=(2026, 8, 14, 0, 0, 0, 0, 0))
    mpos.time = mpos_time

    creatures = types.ModuleType("creatures")
    creatures.CREATURES = []
    creatures.NON_SPREADING_IDS = set()
    creatures.by_id = MagicMock()

    spec = importlib.util.spec_from_file_location(
        "store_profile_under_test", ASSETS / "store.py"
    )
    module = importlib.util.module_from_spec(spec)
    with patch.dict(
        sys.modules,
        {
            "mpos": mpos,
            "mpos.time": mpos_time,
            "pet": MagicMock(),
            "creatures": creatures,
        },
    ):
        spec.loader.exec_module(module)
    return module


class StoreProfileTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.store = load_store()

    def setUp(self):
        _Prefs.data = {}
        _Prefs.commits = 0

    def test_valid_profile_and_legacy_hunter_id_remain_readable(self):
        _Prefs.data["profile"] = {
            "name": "Robin",
            "head": "kikker",  # retired heads deliberately render as the fox
            "accs": ["bril"],
            "bg": 1,
            "hunter_id": "JGR-0042",
        }

        profile = self.store.profile()

        self.assertEqual(profile["head"], "kikker")
        self.assertEqual(profile["hunter_id"], 42)
        self.assertEqual(_Prefs.commits, 0)

    def test_unusable_profile_is_cleared_and_treated_as_unregistered(self):
        malformed_profiles = (
            {"name": "Testjager", "head": 0, "accs": 0, "bg": 0},
            {"name": "Testjager", "head": "vos", "accs": [], "bg": 99},
            {"name": "Testjager", "head": "vos", "accs": [1], "bg": 0},
            7,
        )

        for malformed in malformed_profiles:
            with self.subTest(profile=malformed):
                _Prefs.data = {"profile": malformed}
                _Prefs.commits = 0

                self.assertIsNone(self.store.profile())
                self.assertEqual(_Prefs.data["profile"], {})
                self.assertEqual(_Prefs.commits, 1)


if __name__ == "__main__":
    unittest.main()
