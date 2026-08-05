import importlib.util
import sys
import types
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch


ASSETS = Path(__file__).parents[1] / "be.fri3d.foxhunt" / "assets"


class CompanionProfileSyncTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.store = MagicMock()
        cls.sound = MagicMock()

        mpos = types.ModuleType("mpos")
        mpos.Activity = type("Activity", (), {})
        mpos.Intent = type("Intent", (), {})

        companion = types.ModuleType("companion")
        companion.BGS = [0]
        companion.encode = MagicMock(return_value="H2A001C3")
        cls.companion = companion

        registrar = types.ModuleType("registrar")
        registrar.badge_id = MagicMock(return_value="A4:CF:12:9B:03:7E")

        reg_send = types.ModuleType("screen_reg_send")
        reg_send.RegSendActivity = type("RegSendActivity", (), {})

        modules = {
            "lvgl": MagicMock(),
            "mpos": mpos,
            "ui": MagicMock(),
            "art": MagicMock(),
            "sound": cls.sound,
            "store": cls.store,
            "companion": companion,
            "registrar": registrar,
            "screen_reg_send": reg_send,
        }
        spec = importlib.util.spec_from_file_location(
            "screen_companion_under_test", ASSETS / "screen_companion.py"
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
            "profile", {"profile_pic": "H2A001C3"}
        )
        screen.finish.assert_called_once_with()

    def test_profile_report_uses_auth_user_patch(self):
        store = types.ModuleType("store")
        registrar = types.ModuleType("registrar")
        mpos = types.ModuleType("mpos")
        mpos.TaskManager = MagicMock()
        modules = {"store": store, "registrar": registrar, "mpos": mpos}
        spec = importlib.util.spec_from_file_location(
            "sync_under_test", ASSETS / "sync.py"
        )
        sync = importlib.util.module_from_spec(spec)
        with patch.dict(sys.modules, modules):
            spec.loader.exec_module(sync)

        self.assertEqual(sync._ROUTES["profile"], ("PATCH", "/api/v1/auth/user"))


if __name__ == "__main__":
    unittest.main()
