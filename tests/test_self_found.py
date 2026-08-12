import unittest
from unittest.mock import MagicMock

from hunt_loader import load_screens_hunt


class SelfFoundTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.module, stubs = load_screens_hunt("screens_hunt_self_found")
        cls.store = stubs["store"]
        cls.radio = stubs["fox_radio"].RADIO

    def setUp(self):
        self.store.reset_mock()
        self.radio.reset_mock()

    def test_already_self_found_is_a_local_error(self):
        screen = MagicMock(fox_id=16, entry="1234")
        self.store.zelf_ids.return_value = [16]

        self.module.CodeActivity._submit(screen)

        screen._on_verdict.assert_called_once_with("self")
        self.radio.submit_code.assert_not_called()

    def test_first_direct_find_always_sets_self_bit_and_package(self):
        screen = MagicMock(fox_id=16, c={"rarity": "rare"})
        screen.has_foreground.return_value = False
        self.store.is_caught.return_value = False
        self.store.zelf_gevonden.return_value = {"bes": 2, "noot": 1}

        self.module.CodeActivity._on_verdict(screen, "ok")

        self.store.add_caught.assert_called_once_with(16)
        self.store.zelf_gevonden.assert_called_once_with(16)


if __name__ == "__main__":
    unittest.main()
