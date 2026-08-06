import importlib.util
import sys
import types
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch


ASSETS = Path(__file__).parents[1] / "be.fri3d.foxhunt" / "assets"


class VisitorScreenTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.store = MagicMock()
        cls.sound = MagicMock()

        mpos = types.ModuleType("mpos")
        mpos.Activity = type("Activity", (), {})

        creatures = types.ModuleType("creatures")
        creatures.by_id = MagicMock(
            return_value={"id": 2, "naam": "Kat", "rarity": "norm"}
        )

        modules = {
            "lvgl": MagicMock(),
            "mpos": mpos,
            "art": MagicMock(),
            "sound": cls.sound,
            "store": cls.store,
            "ui": MagicMock(),
            "creatures": creatures,
        }
        spec = importlib.util.spec_from_file_location(
            "screen_visitor_under_test", ASSETS / "screen_visitor.py"
        )
        cls.module = importlib.util.module_from_spec(spec)
        with patch.dict(sys.modules, modules):
            spec.loader.exec_module(cls.module)

    def setUp(self):
        self.store.reset_mock()
        self.sound.reset_mock()

    def test_reveal_claims_pending_visitor_before_showing_creature(self):
        self.store.claim_visitor.return_value = 2
        screen = MagicMock()

        self.module.VisitorActivity._reveal(screen)

        self.store.claim_visitor.assert_called_once_with()
        self.sound.play.assert_called_once_with("caught")
        screen._build_reveal.assert_called_once_with()

    def test_reveal_closes_safely_if_pending_visit_disappeared(self):
        self.store.claim_visitor.return_value = None
        screen = MagicMock()

        self.module.VisitorActivity._reveal(screen)

        self.sound.play.assert_called_once_with("error")
        screen.finish.assert_called_once_with()
        screen._build_reveal.assert_not_called()


if __name__ == "__main__":
    unittest.main()
