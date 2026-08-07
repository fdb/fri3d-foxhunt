import importlib.util
import sys
import types
import unittest
from pathlib import Path
from unittest.mock import patch

ASSETS = Path(__file__).parents[1] / "be.fri3d.foxhunt" / "assets"
sys.path.insert(0, str(ASSETS))


class _Prefs:
    def __init__(self, _name):
        pass

    def get_dict(self, key, default=None):
        return default

    def get_list(self, key, default=None):
        return default


class DebugCodeTest(unittest.TestCase):
    # The debug-code switch lives in store.py (merged from debug_unlock.py
    # for LittleFS block economy), so the test loads store with the same
    # mpos stubs the other store tests use.
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
            "store_debug_under_test", ASSETS / "store.py"
        )
        cls.store = importlib.util.module_from_spec(spec)
        with patch.dict(sys.modules, {"mpos": mpos, "mpos.time": mpos_time}):
            spec.loader.exec_module(cls.store)

    def setUp(self):
        self.store.disable_debug_code()

    def test_debug_code_only_works_after_debug_mode_is_enabled(self):
        s = self.store
        self.assertFalse(s.debug_code_enabled())
        self.assertFalse(s.accepts_debug_code(s.DEBUG_CODE))
        s.enable_debug_code()
        self.assertTrue(s.debug_code_enabled())
        self.assertTrue(s.accepts_debug_code(s.DEBUG_CODE))
        self.assertFalse(s.accepts_debug_code("1234"))


if __name__ == "__main__":
    unittest.main()
