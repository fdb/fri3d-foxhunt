import importlib.util
import sys
import types
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch


ASSETS = Path(__file__).parents[1] / "be.fri3d.foxhunt" / "assets"


class WinScreenTest(unittest.TestCase):
    def _load(self, creature, extras):
        lvgl = MagicMock()
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
        mpos.ui = MagicMock()

        creatures = types.ModuleType("creatures")
        creatures.by_id = MagicMock(return_value=creature)

        celebrate = types.ModuleType("celebrate")
        celebrate.Fireworks = MagicMock()
        celebrate.Stardust = MagicMock()

        modules = {
            "lvgl": lvgl,
            "mpos": mpos,
            "mpos.ui": mpos.ui,
            "ui": ui,
            "art": MagicMock(),
            "creatures": creatures,
            "celebrate": celebrate,
        }
        spec = importlib.util.spec_from_file_location(
            "screen_win_under_test", ASSETS / "screen_win.py"
        )
        module = importlib.util.module_from_spec(spec)
        with patch.dict(sys.modules, modules):
            spec.loader.exec_module(module)

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
