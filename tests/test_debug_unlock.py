import sys
import unittest
from pathlib import Path

ASSETS = Path(__file__).parents[1] / "be.fri3d.foxhunt" / "assets"
sys.path.insert(0, str(ASSETS))

from debug_unlock import (
    DEBUG_CODE,
    accepts_debug_code,
    debug_code_enabled,
    disable_debug_code,
    enable_debug_code,
)


class DebugCodeTest(unittest.TestCase):
    def setUp(self):
        disable_debug_code()

    def test_debug_code_only_works_after_debug_mode_is_enabled(self):
        self.assertFalse(debug_code_enabled())
        self.assertFalse(accepts_debug_code(DEBUG_CODE))
        enable_debug_code()
        self.assertTrue(debug_code_enabled())
        self.assertTrue(accepts_debug_code(DEBUG_CODE))
        self.assertFalse(accepts_debug_code("1234"))


if __name__ == "__main__":
    unittest.main()
