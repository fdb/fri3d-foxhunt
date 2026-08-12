import importlib.util
import re
import unittest
from pathlib import Path


ROOT = Path(__file__).parents[1]
ASSETS = ROOT / "com.enigmeta.foxhunt" / "assets"
ANIMALS = ROOT / "artwork" / "animals"
SERVER_ROSTER = ROOT / "server" / "src" / "lib" / "creatures.ts"


def load_badge_roster():
    spec = importlib.util.spec_from_file_location(
        "creatures_roster_under_test", ASSETS / "creatures.py"
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.CREATURES


def load_server_roster():
    source = SERVER_ROSTER.read_text()
    return [
        {"id": int(cid), "naam": naam, "rarity": rarity}
        for cid, naam, rarity in re.findall(
            r'\{ id: (\d+), naam: "([^"]+)", rarity: "(norm|rare|leg)" \}',
            source,
        )
    ]


class CreatureRosterTest(unittest.TestCase):
    def test_badge_wire_fields_are_unique(self):
        roster = load_badge_roster()

        for field in ("id", "code", "beacon"):
            values = [creature[field] for creature in roster]
            self.assertEqual(len(values), len(set(values)), field)

    def test_every_numbered_animal_sprite_is_in_the_badge_roster(self):
        roster_images = {creature["img"] for creature in load_badge_roster()}
        animal_images = {path.name for path in ANIMALS.glob("[123]_*.png")}

        self.assertEqual(roster_images, animal_images)

    def test_server_roster_matches_badge_identity_name_and_rarity(self):
        badge = [
            {"id": c["id"], "naam": c["naam"], "rarity": c["rarity"]}
            for c in load_badge_roster()
        ]

        self.assertEqual(load_server_roster(), badge)


if __name__ == "__main__":
    unittest.main()
