import types
import unittest
from unittest.mock import MagicMock

from hunt_loader import load_screens_hunt


class SnuffelRulesTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.module, stubs = load_screens_hunt("screens_hunt_snuffel_rules")
        cls.store = stubs["store"]
        cls.link = stubs["snuffel_link"].LINK
        cls.sound = stubs["sound"]

    def setUp(self):
        self.store.reset_mock()
        self.link.reset_mock()
        self.sound.reset_mock()
        self.link._my_mac = "aa:aa:aa:aa:aa:aa"
        self.link.roster = [0, 16]
        self.link.shareable = [0, 16]
        self.link.encounter_key.return_value = "shared-encounter"
        self.store.profile.return_value = {"hunter_id": 42}
        self.store.caught_ids.return_value = [0]

    def peer(self):
        return types.SimpleNamespace(
            mac="bb:bb:bb:bb:bb:bb",
            naam="Mila",
            code="H01A000C1",
            roster=[1],
            shareable=[1],
            is_hunter=False,
        )

    def test_spark_resolves_and_reports_both_directions(self):
        self.store.record_snuffel.return_value = {
            "new_friend": True,
            "vonk": True,
            "dag": "2026-08-07",
            "at": 1_786_100_000,
            "food": "bes",
            "amount": 2,
        }
        self.store.select_vonk_creature.side_effect = [1, 16]
        screen = MagicMock()

        self.module.SnuffelActivity._snuffel(screen, self.peer())

        self.assertEqual(self.store.select_vonk_creature.call_count, 2)
        self.store.add_caught.assert_called_once_with(1, origin="spoor")
        self.store.enqueue_report.assert_called_once_with(
            "snuffel",
            {
                "encounter_id": "shared-encounter",
                "peer": "bb:bb:bb:bb:bb:bb",
                "day": "2026-08-07",
                "occurred_at": 1_786_100_000,
                "vonk": True,
                "sent_creature_id": 16,
                "received_creature_id": 1,
            },
        )

    def test_no_spark_reports_food_only_and_never_selects_a_creature(self):
        self.store.record_snuffel.return_value = {
            "new_friend": False,
            "vonk": False,
            "dag": "2026-08-07",
            "at": 1_786_103_600,
            "food": "noot",
            "amount": 1,
        }
        screen = MagicMock()

        self.module.SnuffelActivity._snuffel(screen, self.peer())

        self.store.select_vonk_creature.assert_not_called()
        self.store.add_caught.assert_not_called()
        report = self.store.enqueue_report.call_args.args[1]
        self.assertFalse(report["vonk"])
        self.assertIsNone(report["sent_creature_id"])
        self.assertIsNone(report["received_creature_id"])


if __name__ == "__main__":
    unittest.main()
