import types
import unittest
from unittest.mock import MagicMock

from hunt_loader import load_screens_hunt


class VisitorScreenTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        creatures = types.ModuleType("creatures")
        creatures.by_id = MagicMock(
            return_value={"id": 2, "naam": "Kat", "rarity": "norm"}
        )
        cls.module, stubs = load_screens_hunt(
            "screens_hunt_visitor_under_test", creatures=creatures
        )
        cls.store = stubs["store"]
        cls.sound = stubs["sound"]

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
