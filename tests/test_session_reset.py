"""foxhunt._new_session — what must not survive one run of the app.

MicroPythonOS re-execs the entrypoint on every startapp and leaves every
sibling module in sys.modules, so a module global set during one launch is
still set in the next. foxhunt.py is the only code that runs fresh, which
makes _new_session() the only place a launch can be recognised as a launch.

Everything it drops is deliberately RAM-only — the debug screen's 1111 code and
cheats, and the fake radio's simulation state — which is exactly why
store.reset_all, an allowlist over the preferences file, cannot reach any of it
by wiping keys. RAM-only is not itself an expiry here: the modules holding that
state are the ones that survive, so something has to say when a run begins.
"""

import importlib.util
from pathlib import Path
import sys
import types
import unittest
from unittest.mock import MagicMock, patch


ASSETS = Path(__file__).parents[1] / "com.enigmeta.foxhunt" / "assets"


def stub_entrypoint_imports():
    """Stand in for everything foxhunt.py imports at entrypoint time.

    mpos.Activity has to be a real class (FoxhuntActivity subclasses it, and a
    MagicMock is not an acceptable base type); the rest only has to exist.
    """
    mpos = types.ModuleType("mpos")
    mpos.Activity = type("Activity", (), {})
    mpos.Intent = type("Intent", (), {})

    creatures = types.ModuleType("creatures")
    creatures.by_id = lambda cid: {"id": cid, "naam": "Vos"}

    store = types.ModuleType("store")
    store.disarmed = []
    store.disable_debug_code = lambda: store.disarmed.append("code")
    store.clear_debug_cheats = lambda: store.disarmed.append("cheats")

    return {
        "lvgl": MagicMock(),
        "mpos": mpos,
        "ui": MagicMock(),
        "art": MagicMock(),
        "store": store,
        "registrar": MagicMock(),
        "telemetry": MagicMock(),
        "creatures": creatures,
    }


def load_foxhunt(stubs):
    spec = importlib.util.spec_from_file_location(
        "foxhunt_under_test", ASSETS / "foxhunt.py"
    )
    module = importlib.util.module_from_spec(spec)
    with patch.dict(sys.modules, stubs):
        spec.loader.exec_module(module)
    return module


class FakeRadioModule(types.ModuleType):
    def __init__(self):
        super().__init__("fox_radio")
        self.resets = 0
        self.RADIO = types.SimpleNamespace(reset=self._reset)

    def _reset(self):
        self.resets += 1


class NewSessionTest(unittest.TestCase):
    def setUp(self):
        self.stubs = stub_entrypoint_imports()
        self.foxhunt = load_foxhunt(self.stubs)

    def run_session(self, extra=None):
        modules = dict(self.stubs)
        modules.update(extra or {})
        with patch.dict(sys.modules, modules):
            if extra is None or "fox_radio" not in extra:
                sys.modules.pop("fox_radio", None)
            self.foxhunt._new_session()

    def test_a_launch_disarms_everything_the_debug_screen_can_arm(self):
        # The 1111 code and the cheats alike. Kept in RAM on purpose, so
        # nothing in the preferences file wipes them — and RAM is not by
        # itself an expiry, since store.py survives the relaunch that this
        # runs on. Neither may be waiting for whoever picks the badge up next.
        self.run_session()
        self.assertEqual(self.stubs["store"].disarmed, ["code", "cheats"])

    def test_a_launch_resets_a_radio_left_over_from_the_last_one(self):
        radio = FakeRadioModule()
        self.run_session({"fox_radio": radio})
        self.assertEqual(radio.resets, 1)

    def test_a_cold_launch_does_not_import_the_radio_to_reset_it(self):
        # Nothing loaded holds no session to drop, and pulling fox_radio in
        # here would spend a LittleFS open (~0.25s) of every cold start on an
        # empty singleton. The debug state still gets dropped either way.
        self.run_session()
        self.assertNotIn("fox_radio", sys.modules)
        self.assertEqual(self.stubs["store"].disarmed, ["code", "cheats"])


if __name__ == "__main__":
    unittest.main()
