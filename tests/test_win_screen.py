import types
import unittest
from unittest.mock import MagicMock

from hunt_loader import load_screens_hunt


class WinScreenTest(unittest.TestCase):
    def _load(self, creature, extras):
        ui = MagicMock()
        screen = MagicMock()
        ui.make_screen.return_value = screen

        class Activity:
            def getIntent(self):
                return types.SimpleNamespace(extras=extras)

            def setContentView(self, content):
                self.content = content

        mpos = types.ModuleType("mpos")
        mpos.Activity = Activity
        mpos.Intent = type("Intent", (), {})
        mpos.ui = MagicMock()

        creatures = types.ModuleType("creatures")
        creatures.by_id = MagicMock(return_value=creature)

        celebrate = types.ModuleType("celebrate")
        celebrate.Fireworks = MagicMock()
        celebrate.Stardust = MagicMock()

        module, _ = load_screens_hunt(
            "screens_hunt_win_under_test",
            mpos=mpos,
            **{"mpos.ui": mpos.ui},
            ui=ui,
            creatures=creatures,
            celebrate=celebrate,
        )
        return module, celebrate, screen

    def test_legendary_refind_keeps_legendary_payoff_and_package(self):
        creature = {"id": 12, "naam": "Knoricorn", "rarity": "leg"}
        pakket = {"bes": 2, "noot": 1}
        module, celebrate, screen = self._load(
            creature, {"fox_id": 12, "pakket": pakket}
        )

        activity = module.WinActivity()
        activity.onCreate()

        celebrate.Fireworks.assert_called_once_with(
            screen,
            creature,
            detail="zelf gevonden - pakket: +2 bes  +1 noot",
        )
        celebrate.Stardust.assert_not_called()
        self.assertIs(activity.fx, celebrate.Fireworks.return_value)


if __name__ == "__main__":
    unittest.main()
