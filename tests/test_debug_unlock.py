import sys
import unittest
from pathlib import Path

ASSETS = Path(__file__).parents[1] / "be.fri3d.foxhunt" / "assets"
sys.path.insert(0, str(ASSETS))

from debug_unlock import DebugUnlock


class DebugUnlockTest(unittest.TestCase):
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


if __name__ == "__main__":
    unittest.main()
