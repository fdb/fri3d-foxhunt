import sys
import unittest
from pathlib import Path

ASSETS = Path(__file__).parents[1] / "be.fri3d.foxhunt" / "assets"
sys.path.insert(0, str(ASSETS))

from debug_unlock import (
    DEBUG_CODE,
    DebugUnlock,
    accepts_debug_code,
    debug_code_enabled,
    disable_debug_code,
    enable_debug_code,
)


class DebugUnlockTest(unittest.TestCase):
    def setUp(self):
        disable_debug_code()

    def test_exact_sequence_unlocks(self):
        unlock = DebugUnlock()
        for code in ("1", "22", "333"):
            unlock.cleared(code)
        self.assertTrue(unlock.entered("4444"))

    def test_wrong_clear_resets_progress(self):
        unlock = DebugUnlock()
        unlock.cleared("1")
        unlock.cleared("2")
        unlock.cleared("333")
        self.assertFalse(unlock.entered("4444"))

    def test_normal_four_digit_code_does_not_unlock(self):
        unlock = DebugUnlock()
        self.assertFalse(unlock.entered("1234"))

    def test_unlock_is_one_shot(self):
        unlock = DebugUnlock()
        for code in ("1", "22", "333"):
            unlock.cleared(code)
        self.assertTrue(unlock.entered("4444"))
        self.assertFalse(unlock.entered("4444"))

    def test_debug_code_only_works_after_debug_mode_is_enabled(self):
        self.assertFalse(debug_code_enabled())
        self.assertFalse(accepts_debug_code(DEBUG_CODE))
        enable_debug_code()
        self.assertTrue(debug_code_enabled())
        self.assertTrue(accepts_debug_code(DEBUG_CODE))
        self.assertFalse(accepts_debug_code("1234"))


if __name__ == "__main__":
    unittest.main()
