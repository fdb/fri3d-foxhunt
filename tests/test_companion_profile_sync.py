import asyncio
import importlib.util
import sys
import types
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch


ASSETS = Path(__file__).parents[1] / "com.enigmeta.foxhunt" / "assets"


class CompanionProfileSyncTest(unittest.TestCase):
    # The companion and register screens live in screens_onboarding.py
    # (merged for LittleFS block economy), so the stub set covers the whole
    # onboarding group's import surface.
    @classmethod
    def setUpClass(cls):
        cls.store = MagicMock()
        cls.sound = MagicMock()

        mpos = types.ModuleType("mpos")
        mpos.Activity = type("Activity", (), {})
        mpos.Intent = type("Intent", (), {})
        mpos_ui = types.ModuleType("mpos.ui")
        keyboard = types.ModuleType("mpos.ui.keyboard")
        keyboard.MposKeyboard = MagicMock()

        companion = types.ModuleType("companion")
        companion.BGS = [0]
        companion.HEADS = [{"id": "vos", "naam": "Vos"}]
        companion.src = MagicMock(return_value="companions/vos.png")
        companion.encode = MagicMock(return_value="H02A001C3")
        cls.companion = companion

        cls.lvgl = MagicMock()
        cls.ui = MagicMock()

        registrar = types.ModuleType("registrar")
        registrar.badge_id = MagicMock(return_value="A4:CF:12:9B:03:7E")
        registrar.has_lora = MagicMock(return_value=False)
        registrar.hunter_label = MagicMock(return_value=None)
        registrar.REGISTRAR = MagicMock()
        registrar.flush = MagicMock()
        cls.registrar = registrar

        creatures = types.ModuleType("creatures")
        creatures.by_id = MagicMock()

        modules = {
            "lvgl": cls.lvgl,
            "mpos": mpos,
            "mpos.ui": mpos_ui,
            "mpos.ui.keyboard": keyboard,
            "ui": cls.ui,
            "art": MagicMock(),
            "sound": cls.sound,
            "store": cls.store,
            "companion": companion,
            "registrar": registrar,
            "creatures": creatures,
        }
        spec = importlib.util.spec_from_file_location(
            "screens_onboarding_under_test", ASSETS / "screens_onboarding.py"
        )
        cls.module = importlib.util.module_from_spec(spec)
        with patch.dict(sys.modules, modules):
            spec.loader.exec_module(cls.module)

    def setUp(self):
        self.store.reset_mock()
        self.sound.reset_mock()
        self.companion.encode.reset_mock()
        self.registrar.flush.reset_mock()

    def _register_text(self, has_lora):
        self.ui.reset_mock()
        self.registrar.has_lora.return_value = has_lora
        self.store.profile.return_value = None
        screen = MagicMock()
        screen.getIntent.return_value.extras = {}

        self.module.RegisterActivity.onCreate(screen)

        banner = self.ui.banner.call_args.args[1]
        labels = [call.args[1] for call in self.ui.label.call_args_list]
        return banner, labels

    def test_register_welcomes_every_role_and_shows_collector_without_lora(self):
        banner, labels = self._register_text(has_lora=False)

        self.assertEqual(banner, "WELKOM!")
        self.assertIn("VERZAMELAAR", labels)
        self.assertNotIn("JAGER ID", labels)
        self.assertNotIn("volgt", labels)

    def test_register_only_promises_hunter_id_when_lora_is_present(self):
        _, labels = self._register_text(has_lora=True)

        self.assertIn("JAGER ID", labels)
        self.assertIn("volgt", labels)
        self.assertNotIn("VERZAMELAAR", labels)

    def test_edit_saves_locally_and_queues_shortcode_patch(self):
        screen = MagicMock(edit=True, head="uil", accs=["bril"], bg=2)

        self.module.CompanionActivity._register(screen)

        self.companion.encode.assert_called_once_with("uil", ["bril"], 2)
        self.store.update_profile.assert_called_once_with(
            head="uil", accs=["bril"], bg=2
        )
        self.store.enqueue_report.assert_called_once_with(
            "profile", {"profile_pic": "H02A001C3"}
        )
        self.registrar.flush.assert_called_once_with()
        screen.finish.assert_called_once_with()

    def test_head_grid_scrolls_vertically(self):
        grid = MagicMock()
        self.ui.row.return_value = grid
        screen = MagicMock(screen=MagicMock(), head="vos")

        self.module.CompanionActivity._build_heads(screen)

        grid.add_flag.assert_called_once_with(self.lvgl.obj.FLAG.SCROLLABLE)
        grid.set_scroll_dir.assert_called_once_with(self.lvgl.DIR.VER)

    def test_name_edit_saves_locally_and_queues_name_patch(self):
        """NAAM WIJZIGEN is the same promise as the maatje edit: the name is
        what /scores shows in public, so a rename that only lands locally
        leaves the scoreboard calling the player something they dropped."""
        screen = MagicMock(edit=True)
        screen._name.return_value = "Vosje"

        self.module.RegisterActivity._next(screen)

        self.store.update_profile.assert_called_once_with(name="Vosje")
        self.store.enqueue_report.assert_called_once_with("profile", {"name": "Vosje"})
        screen.finish.assert_called_once_with()

    # The outbox drain (_ROUTES) lives in registrar.py since sync.py was
    # merged into it for LittleFS block economy.
    def _load_registrar(self, name):
        lvgl = types.ModuleType("lvgl")
        mpos = types.ModuleType("mpos")
        mpos.TaskManager = MagicMock()
        spec = importlib.util.spec_from_file_location(name, ASSETS / "registrar.py")
        registrar = importlib.util.module_from_spec(spec)
        with patch.dict(sys.modules, {"lvgl": lvgl, "mpos": mpos}):
            spec.loader.exec_module(registrar)
        return registrar

    def _load_routes(self, name):
        return self._load_registrar(name)._ROUTES

    def test_restore_preserves_self_found_provenance(self):
        registrar = self._load_registrar("registrar_restore_self_under_test")
        store = MagicMock()
        store.restore_caught.return_value = [0, 16]
        companion = types.ModuleType("companion")
        companion.decode = MagicMock(return_value=("vos", [], 0))

        with patch.dict(sys.modules, {"store": store, "companion": companion}):
            registrar.adopt(
                "aa:bb:cc:dd:ee:ff",
                {
                    "name": "Sam",
                    "creatures": [0, 16],
                    "self_found": [16],
                    "found_dates": {"0": "2026-08-06", "16": "2026-08-07"},
                    "self_found_dates": {"16": "2026-08-08"},
                },
            )

        store.restore_caught.assert_called_once_with(
            [0, 16],
            [16],
            {"0": "2026-08-06", "16": "2026-08-07"},
            {"16": "2026-08-08"},
        )

    def test_restore_reconciles_authoritative_help_state(self):
        registrar = self._load_registrar("registrar_restore_help_under_test")
        store = MagicMock()
        store.restore_caught.return_value = []
        companion = types.ModuleType("companion")
        companion.decode = MagicMock(return_value=("vos", [], 0))

        with patch.dict(sys.modules, {"store": store, "companion": companion}):
            registrar.adopt(
                "aa:bb:cc:dd:ee:ff",
                {
                    "name": "Sam",
                    "players_helped": 2,
                    "helped_encounters": ["enc-a", "enc-b"],
                },
            )

        store.reconcile_help.assert_called_once_with(2, ["enc-a", "enc-b"])

    def test_profile_report_uses_auth_user_patch(self):
        routes = self._load_routes("registrar_profile_under_test")
        self.assertEqual(routes["profile"], ("PATCH", "/api/v1/auth/user"))

    def test_pluk_report_uses_player_pluk_route(self):
        routes = self._load_routes("registrar_pluk_under_test")
        self.assertEqual(routes["pluk"], ("POST", "/api/v1/player/pluk"))

    def test_visitor_report_uses_player_visitor_route(self):
        routes = self._load_routes("registrar_visitor_under_test")
        self.assertEqual(routes["visitor"], ("POST", "/api/v1/player/visitor"))

    def test_pending_help_syncs_even_after_its_report_left_the_outbox(self):
        registrar = self._load_registrar("registrar_pending_help_under_test")
        store = MagicMock()
        store.outbox.return_value = []
        store.help_counts.return_value = (0, 1)

        async def request(method, path, body=None):
            self.assertEqual(method, "GET")
            self.assertIn("/api/v1/auth/user?badge_id=", path)
            self.assertIsNone(body)
            return 200, {
                "players_helped": 1,
                "helped_encounters": ["enc-a"],
            }

        registrar._json_request = request
        with patch.dict(sys.modules, {"store": store}):
            asyncio.run(registrar._drain())

        store.reconcile_help.assert_called_once_with(1, ["enc-a"])

    def test_flush_schedules_reconciliation_when_only_pending_help_remains(self):
        registrar = self._load_registrar("registrar_flush_help_under_test")
        store = MagicMock()
        store.outbox.return_value = []
        store.help_counts.return_value = (0, 1)
        registrar.TaskManager.create_task.side_effect = lambda task: task.close()

        with patch.dict(sys.modules, {"store": store}):
            registrar.flush()

        registrar.TaskManager.create_task.assert_called_once()

    def test_old_server_snapshot_does_not_erase_confirmed_help(self):
        registrar = self._load_registrar("registrar_old_help_server_under_test")
        store = MagicMock()
        store.outbox.return_value = []
        store.help_counts.return_value = (2, 1)

        async def request(_method, _path, body=None):
            self.assertIsNone(body)
            return 200, {"name": "old server without help fields"}

        registrar._json_request = request
        with patch.dict(sys.modules, {"store": store}):
            asyncio.run(registrar._drain())

        store.reconcile_help.assert_not_called()


if __name__ == "__main__":
    unittest.main()
