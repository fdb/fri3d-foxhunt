import sys
import unittest
from pathlib import Path
from unittest.mock import MagicMock

ASSETS = Path(__file__).parents[1] / "be.fri3d.foxhunt" / "assets"
sys.path.insert(0, str(ASSETS))

sys.modules.setdefault("lvgl", MagicMock())
sys.modules.setdefault("mpos", MagicMock())

import companion  # noqa: E402


class CompanionRosterTest(unittest.TestCase):
    """The roster's art contract: id == aseprite layer == <id>.png.

    Nothing at runtime notices a missing PNG — LVGL just draws nothing, and a
    hoed that silently stopped existing is exactly the kind of thing you find
    on the badge at the festival instead of here."""

    def test_every_head_and_accessory_has_baked_art(self):
        for part in companion.HEADS + companion.ACCS:
            png = ASSETS / "companions" / (part["id"] + ".png")
            self.assertTrue(png.is_file(), "missing art for %s" % part["id"])

    def test_no_stray_companion_art(self):
        # The other direction: a PNG nothing references is either a typo in an
        # id or a layer that never made it into the roster.
        ids = {p["id"] for p in companion.HEADS + companion.ACCS}
        stray = {
            f.stem for f in (ASSETS / "companions").glob("*.png") if f.stem not in ids
        }
        self.assertEqual(stray, set())

    def test_unlocks_climb_in_roster_order(self):
        # ACCS order is draw order AND wire-bit order; the unlock ladder rides
        # along, so the fanciest layers are also the last ones you earn.
        unlocks = [a["unlock"] for a in companion.ACCS]
        self.assertEqual(unlocks, sorted(unlocks))
        self.assertEqual(unlocks[0], 0)  # something to build a maatje from
        self.assertEqual(companion.ACCS[-1]["id"], "sterren")  # the top prize

    def test_is_unlocked_opens_exactly_on_the_threshold(self):
        sterren = companion.ACCS[-1]
        self.assertFalse(companion.is_unlocked(sterren, sterren["unlock"] - 1))
        self.assertTrue(companion.is_unlocked(sterren, sterren["unlock"]))


if __name__ == "__main__":
    unittest.main()
