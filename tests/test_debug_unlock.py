import importlib.util
import sys
import types
import unittest
from pathlib import Path
from unittest.mock import patch

ASSETS = Path(__file__).parents[1] / "com.enigmeta.foxhunt" / "assets"
sys.path.insert(0, str(ASSETS))


class _Prefs:
    """A preferences file that records every read, so a test can show that
    something never goes near it."""

    reads = []

    def __init__(self, _name):
        pass

    def get_dict(self, key, default=None):
        _Prefs.reads.append(key)
        return default

    def get_list(self, key, default=None):
        _Prefs.reads.append(key)
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
        self.store.clear_debug_cheats()
        _Prefs.reads.clear()

    def test_debug_code_only_works_after_debug_mode_is_enabled(self):
        s = self.store
        self.assertFalse(s.debug_code_enabled())
        self.assertFalse(s.accepts_debug_code(s.DEBUG_CODE))
        s.enable_debug_code()
        self.assertTrue(s.debug_code_enabled())
        self.assertTrue(s.accepts_debug_code(s.DEBUG_CODE))
        self.assertFalse(s.accepts_debug_code("1234"))

    def test_an_armed_cheat_never_reaches_the_preferences_file(self):
        # Nothing written is nothing to inherit: a badge that is power-cycled
        # or reflashed comes back with the cheats off, with no key to wipe.
        s = self.store
        s.set_debug_cheat("nooit_moe", True)
        self.assertTrue(s.debug_cheat("nooit_moe"))
        self.assertEqual(_Prefs.reads, [])

    def test_clearing_disarms_every_cheat_at_once(self):
        # The launch and wipe paths call this without naming names, so a cheat
        # added later is covered by it the day it is added.
        s = self.store
        s.set_debug_cheat("nooit_moe", True)
        s.set_debug_cheat("een_latere_cheat", True)

        s.clear_debug_cheats()

        self.assertFalse(s.debug_cheat("nooit_moe"))
        self.assertFalse(s.debug_cheat("een_latere_cheat"))

    def test_an_unarmed_cheat_is_false_rather_than_missing(self):
        # Callers use it straight in a boolean (store.py's nooit_moe rule),
        # never through a .get with a default.
        self.assertIs(self.store.debug_cheat("nooit_moe"), False)
        self.assertIs(self.store.debug_cheat("never_defined"), False)


if __name__ == "__main__":
    unittest.main()
