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
        registrar.REGISTRAR = MagicMock()

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
    def _load_routes(self, name):
        lvgl = types.ModuleType("lvgl")
        mpos = types.ModuleType("mpos")
        mpos.TaskManager = MagicMock()
        spec = importlib.util.spec_from_file_location(name, ASSETS / "registrar.py")
        registrar = importlib.util.module_from_spec(spec)
        with patch.dict(sys.modules, {"lvgl": lvgl, "mpos": mpos}):
            spec.loader.exec_module(registrar)
        return registrar._ROUTES

    def test_profile_report_uses_auth_user_patch(self):
        routes = self._load_routes("registrar_profile_under_test")
        self.assertEqual(routes["profile"], ("PATCH", "/api/v1/auth/user"))

    def test_pluk_report_uses_player_pluk_route(self):
        routes = self._load_routes("registrar_pluk_under_test")
        self.assertEqual(routes["pluk"], ("POST", "/api/v1/player/pluk"))

    def test_visitor_report_uses_player_visitor_route(self):
        routes = self._load_routes("registrar_visitor_under_test")
        self.assertEqual(routes["visitor"], ("POST", "/api/v1/player/visitor"))


if __name__ == "__main__":
    unittest.main()
