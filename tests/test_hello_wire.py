import sys
import unittest
from pathlib import Path
from unittest.mock import MagicMock

ASSETS = Path(__file__).parents[1] / "be.fri3d.foxhunt" / "assets"
sys.path.insert(0, str(ASSETS))

# The wire codec is pure data, but hello_link.py imports lvgl for its timers
# and builds the LINK singleton at import (which falls back to FakeHelloLink
# on the host, where espnow doesn't exist). Stubbing lvgl keeps both happy.
sys.modules.setdefault("lvgl", MagicMock())
sys.modules.setdefault("mpos", MagicMock())

import hello_link  # noqa: E402


class HelloWireTest(unittest.TestCase):
    def test_documented_example(self):
        # The format's reference vector from GAME_DESIGN.md.
        self.assertEqual(
            hello_link.encode_hello("Noor", "H2A084C3"),
            b"FXH1|hello|Noor|H2A084C3",
        )
        self.assertEqual(
            hello_link.decode(b"FXH1|hello|Noor|H2A084C3"),
            {"kind": "hello", "name": "Noor", "companion": "H2A084C3"},
        )

    def test_round_trip(self):
        frame = hello_link.encode_hello("Sam", "H1A000C1")
        hello = hello_link.decode(frame)
        self.assertEqual(hello["name"], "Sam")
        self.assertEqual(hello["companion"], "H1A000C1")

    def test_name_cannot_smuggle_the_field_separator(self):
        # A pipe in a name would shift every later field; it becomes a space.
        frame = hello_link.encode_hello("No|or\nx", "H1A000C1")
        self.assertEqual(hello_link.decode(frame)["name"], "No or x")

    def test_name_is_bounded(self):
        frame = hello_link.encode_hello("x" * 200, "H1A000C1")
        self.assertLessEqual(len(hello_link.decode(frame)["name"]), hello_link.NAME_MAX)

    def test_empty_name_survives(self):
        self.assertEqual(
            hello_link.decode(hello_link.encode_hello(None, "H1A000C1"))["name"], ""
        )

    def test_foreign_traffic_is_ignored(self):
        # ESP-NOW broadcast is a party line: anything not ours decodes to None.
        for junk in (
            b"",
            b"hi there",
            b"XXXX|hello|Noor|H2A084C3",  # wrong magic
            b"FXH1|hello|Noor",  # missing field
            b"FXH1|hello|Noor|H2A084C3|extra",  # extra field
            b"FXH1|spoor|Noor|H2A084C3",  # future kind: unknown today
            b"\xff\xfe\x00",  # not even UTF-8
            None,
        ):
            self.assertIsNone(hello_link.decode(junk), repr(junk))

    def test_frames_fit_espnow(self):
        # ESP-NOW payloads cap at 250 bytes; a maximal hello stays well under.
        frame = hello_link.encode_hello("x" * 200, "H2A084C3")
        self.assertLessEqual(len(frame), 250)

    def test_fake_link_speaks_the_real_wire(self):
        # The fake cast goes through encode/decode, so the emulator can never
        # show a hello the badge couldn't parse — including valid shortcodes.
        import companion

        link = hello_link.FakeHelloLink()
        heard = []
        link.start({"name": "Ik", "companion": "H1A000C1"}, heard.append)
        for _ in link.CAST:
            link.simulate_hello()
        self.assertEqual(len(heard), len(link.CAST))
        default = (companion.HEADS[0]["id"], [], 0)
        for peer, (name, code) in zip(heard, link.CAST):
            self.assertEqual(peer["name"], name)
            self.assertEqual(peer["companion"], code)
            # every cast shortcode must decode to a real, non-default maatje
            self.assertNotEqual(companion.decode(code), default, code)
        link.stop()
        link.simulate_hello()  # stopped: must not call a dead listener
        self.assertEqual(len(heard), len(link.CAST))


if __name__ == "__main__":
    unittest.main()
