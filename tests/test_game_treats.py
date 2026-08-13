"""A mid-game hapje must never write to flash inside the tick.

The write is what the player felt as a hitch (config.json is rewritten whole on
every commit), so take_treat only pockets the hapje and bank_treats() commits a
whole round in one go. These tests pin both halves: nothing is written while the
game runs, and nothing is lost at either exit — the end card or walking out.
"""

import importlib.util
import sys
import types
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

ASSETS = Path(__file__).parents[1] / "com.enigmeta.foxhunt" / "assets"
sys.path.insert(0, str(ASSETS))


def load_screens_care(name="screens_care_under_test"):
    """Load screens_care.py against a stub set (same recipe as hunt_loader)."""
    mpos = types.ModuleType("mpos")
    # the lifecycle hooks are real no-ops, not MagicMocks: GameActivity.onPause
    # calls super().onPause(), and zero-arg super() needs a genuine base class
    mpos.Activity = type(
        "Activity",
        (),
        {
            "onResume": lambda self, screen: None,
            "onPause": lambda self, screen: None,
        },
    )
    mpos.Intent = type("Intent", (), {})
    mpos.ui = MagicMock()

    celebrate = types.ModuleType("celebrate")
    celebrate.Fireworks = MagicMock()
    celebrate.Stardust = MagicMock()

    sound = MagicMock()  # also serves `import sound as leds`

    stubs = {
        "lvgl": MagicMock(),
        "mpos": mpos,
        "mpos.ui": mpos.ui,
        "ui": MagicMock(),
        "art": MagicMock(),
        "sound": sound,
        "store": MagicMock(),
        "pet": MagicMock(),
        "companion": MagicMock(),
        "celebrate": celebrate,
    }
    spec = importlib.util.spec_from_file_location(name, ASSETS / "screens_care.py")
    module = importlib.util.module_from_spec(spec)
    with patch.dict(sys.modules, stubs):
        spec.loader.exec_module(module)
    return module, stubs


class GameTreatTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.module, stubs = load_screens_care()
        cls.store = stubs["store"]
        cls.sound = stubs["sound"]

    def setUp(self):
        self.store.reset_mock()
        self.sound.reset_mock()
        self.store.FOODS = ("bes", "noot", "eikel")
        self.game = MagicMock()
        self.game._pocket = []
        self.game._bonus = 0
        self.game.score = 0
        self.game.TICK_MS = 50

    def take(self, food):
        self.module.GameActivity.take_treat(self.game, food)

    def test_catching_pockets_the_hapje_without_touching_flash(self):
        self.take("bes")

        self.assertEqual(self.game._pocket, ["bes"])
        self.store.add_foods.assert_not_called()
        self.store.add_food.assert_not_called()
        # the player still gets the whole payoff on the spot
        self.sound.play.assert_called_once_with("caught")
        self.game.toast_l.set_text.assert_called_once_with("+1 bes!")
        self.game.set_score.assert_called_once_with(1)
        self.assertEqual(self.game._bonus, 1)

    def test_a_round_banks_in_one_write(self):
        self.take("bes")
        self.take("noot")
        self.take("bes")

        self.module.GameActivity.bank_treats(self.game)

        self.store.add_foods.assert_called_once_with(["bes", "noot", "bes"])
        self.assertEqual(self.game._pocket, [])

    def test_banking_an_empty_pocket_writes_nothing(self):
        self.module.GameActivity.bank_treats(self.game)
        self.store.add_foods.assert_not_called()

    def test_game_over_banks_the_round(self):
        self.game._grabbed = False
        self.module.GameActivity.game_over(self.game, "klaar")
        self.game.bank_treats.assert_called_once_with()

    def test_leaving_mid_round_banks_what_was_caught(self):
        # a real instance, because onPause chains through zero-arg super().
        # __new__ skips onCreate, so every attribute onPause reads has to be
        # laid out by hand here — which is exactly how this test went stale:
        # onPause learned to cancel the after-render collect timer a day after
        # this was written, and a bare instance has no _gc_timer to cancel.
        # Anything new that onPause touches needs a line here too.
        game = self.module.GameActivity.__new__(self.module.GameActivity)
        game.timer = None
        game._gc_timer = None
        game.bank_treats = MagicMock()

        self.module.GameActivity.onPause(game, MagicMock())

        game.bank_treats.assert_called_once_with()


class StoreAddFoodsTest(unittest.TestCase):
    """add_food is now one shape of add_foods, and both commit exactly once."""

    def setUp(self):
        spec = importlib.util.spec_from_file_location(
            "store_under_test", ASSETS / "store.py"
        )
        self.store = importlib.util.module_from_spec(spec)
        stubs = {
            "mpos": MagicMock(),
            "mpos.time": MagicMock(),
            "creatures": __import__("creatures"),
            "pet": MagicMock(),
            "companion": MagicMock(),
        }
        with patch.dict(sys.modules, stubs):
            spec.loader.exec_module(self.store)

    def test_add_foods_counts_repeats_and_commits_once(self):
        prefs = MagicMock()
        editor = prefs.edit.return_value
        with patch.object(self.store, "voorraad", return_value={"bes": 1, "noot": 0}):
            with patch.object(self.store, "SharedPreferences", return_value=prefs):
                out = self.store.add_foods(["bes", "bes", "noot"])

        self.assertEqual(out, {"bes": 3, "noot": 1})
        editor.put_dict.assert_called_once_with("voorraad", {"bes": 3, "noot": 1})
        editor.put_dict.return_value.commit.assert_called_once_with()

    def test_add_food_with_n_still_adds_n(self):
        prefs = MagicMock()
        with patch.object(self.store, "voorraad", return_value={"eikel": 0}):
            with patch.object(self.store, "SharedPreferences", return_value=prefs):
                out = self.store.add_food("eikel", 3)

        self.assertEqual(out, {"eikel": 3})
        prefs.edit.assert_called_once_with()  # one instance, one editor, one write


if __name__ == "__main__":
    unittest.main()
