"""The entry activity routes without ever putting a screen on the stack."""

import importlib.util
from pathlib import Path
import sys
import types
import unittest
from unittest.mock import MagicMock, patch


ASSETS = Path(__file__).parents[1] / "com.enigmeta.foxhunt" / "assets"


class Intent:
    def __init__(self, activity_class=None):
        self.activity_class = activity_class


class Activity:
    def __init__(self):
        self.launches = []

    def setContentView(self, _screen):
        raise AssertionError("the router must never render a screen")

    def startActivityForResult(self, intent, callback):
        self.launches.append((intent.activity_class, callback))


def load_entry(profile):
    mpos = types.ModuleType("mpos")
    mpos.Activity = Activity
    mpos.Intent = Intent

    store = types.ModuleType("store")
    store.current_profile = profile
    store.profile = lambda: store.current_profile
    store.disable_debug_code = MagicMock()
    store.clear_debug_cheats = MagicMock()

    registrar = types.ModuleType("registrar")
    registrar.resync = MagicMock()
    telemetry = types.ModuleType("telemetry")
    telemetry.boot = MagicMock()

    stubs = {
        "mpos": mpos,
        "store": store,
        "registrar": registrar,
        "telemetry": telemetry,
    }
    spec = importlib.util.spec_from_file_location(
        "foxhunt_routing_under_test", ASSETS / "foxhunt.py"
    )
    module = importlib.util.module_from_spec(spec)
    with patch.dict(sys.modules, stubs):
        sys.modules.pop("fox_radio", None)
        spec.loader.exec_module(module)

    welcome = type("WelcomeActivity", (), {})
    home = type("HomeActivity", (), {})
    targets = {
        "screens_onboarding": types.SimpleNamespace(WelcomeActivity=welcome),
        "screens_system": types.SimpleNamespace(HomeActivity=home),
    }
    module.lazy = targets.__getitem__
    return module, store, registrar, telemetry, welcome, home


class EntryRoutingTest(unittest.TestCase):
    def test_unregistered_launch_opens_welcome_without_rendering(self):
        module, _store, registrar, telemetry, welcome, _home = load_entry(None)
        router = module.FoxhuntActivity()

        router.onCreate()

        self.assertEqual(router.launches[0][0], welcome)
        telemetry.boot.assert_called_once_with()
        registrar.resync.assert_called_once_with()

    def test_registered_launch_opens_home_without_rendering(self):
        module, _store, _registrar, _telemetry, _welcome, home = load_entry(
            {"name": "Sam"}
        )
        router = module.FoxhuntActivity()

        router.onCreate()

        self.assertEqual(router.launches[0][0], home)

    def test_registration_result_reroutes_to_home(self):
        module, store, _registrar, _telemetry, welcome, home = load_entry(None)
        router = module.FoxhuntActivity()
        router.onCreate()
        self.assertEqual(router.launches[0][0], welcome)

        store.current_profile = {"name": "Sam"}
        router.launches[0][1]({"result_code": "registered"})

        self.assertEqual(router.launches[1][0], home)

    def test_wipe_result_reroutes_to_welcome(self):
        module, store, _registrar, _telemetry, welcome, home = load_entry(
            {"name": "Sam"}
        )
        router = module.FoxhuntActivity()
        router.onCreate()
        self.assertEqual(router.launches[0][0], home)

        store.current_profile = None
        router.launches[0][1]({"result_code": "unregistered"})

        self.assertEqual(router.launches[1][0], welcome)


if __name__ == "__main__":
    unittest.main()
