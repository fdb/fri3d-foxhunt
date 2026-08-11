import sys
import unittest
from pathlib import Path
from unittest.mock import MagicMock

ASSETS = Path(__file__).parents[1] / "com.enigmeta.foxhunt" / "assets"
sys.path.insert(0, str(ASSETS))

# The shortcode codec is pure data, but it lives in companion.py next to the
# rosters it indexes into — and companion.py reaches the graphics stack through
# art/ui (ui builds its shared lv.style_t objects at import time). Stubbing
# those two lets the codec be tested on the host, where the badge isn't.
sys.modules.setdefault("lvgl", MagicMock())
sys.modules.setdefault("mpos", MagicMock())

import companion  # noqa: E402


class CompanionCodeTest(unittest.TestCase):
    def test_documented_example(self):
        # The format's reference vector: head 1, bril + strik, backdrop 1.
        self.assertEqual(companion.encode("vos", ["bril", "strik"], 0), "H1A003C1")
        self.assertEqual(companion.decode("H1A003C1"), ("vos", ["bril", "strik"], 0))

    def test_round_trips_every_head_and_backdrop(self):
        for h, head in enumerate(companion.HEADS):
            for bg in range(len(companion.BGS)):
                code = companion.encode(head["id"], [], bg)
                self.assertEqual(companion.decode(code), (head["id"], [], bg), code)
            self.assertEqual(code[1], str(h + 1))  # 1-based, never 0

    def test_round_trips_every_accessory(self):
        for aid in companion._ACCS_WIRE:
            code = companion.encode("vos", [aid], 0)
            self.assertEqual(companion.decode(code), ("vos", [aid], 0), code)

    def test_all_accessories_at_once_fits_the_mask(self):
        every = list(companion._ACCS_WIRE)
        code = companion.encode("varken", every, 6)
        self.assertEqual(len(code), 8)
        self.assertEqual(companion.decode(code), ("varken", every, 6))

    def test_geen_is_not_an_accessory_bit(self):
        # "geen" is the builder screen's take-it-all-off tile, not a member of
        # the roster; it must never consume a bit, or every accessory shifts.
        self.assertNotIn("geen", companion._ACCS_WIRE)
        self.assertEqual(companion.encode("vos", ["geen"], 0), "H1A000C1")

    def test_mask_is_hex_wide_enough_for_the_roster(self):
        # Three hex digits = 12 bits. If the roster ever outgrows that, the
        # format needs a fourth digit, not a silently truncated mask.
        self.assertLessEqual(len(companion._ACCS_WIRE), 12)

    def test_malformed_codes_fall_back_to_the_default(self):
        default = (companion.HEADS[0]["id"], [], 0)
        for bad in (None, "", "H1A003", "X1A003C1", "H1B003C1", "H1A00ZC1", 12345):
            self.assertEqual(companion.decode(bad), default, repr(bad))

    def test_out_of_range_indices_degrade_instead_of_crashing(self):
        # A badge reading a code minted by a newer roster keeps rendering.
        head, accs, bg = companion.decode("H9AFFFC9")
        self.assertEqual(head, companion.HEADS[0]["id"])
        self.assertEqual(bg, 0)
        self.assertEqual(accs, list(companion._ACCS_WIRE))

    def test_unknown_head_encodes_as_the_default(self):
        self.assertEqual(companion.encode("draak", [], 0), "H1A000C1")


if __name__ == "__main__":
    unittest.main()
