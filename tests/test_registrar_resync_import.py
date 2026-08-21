"""resync() must reach companion.py on a COLD launch.

The trap this guards is invisible on a warm badge. MicroPythonOS re-execs the
entrypoint on every startapp but leaves sibling modules in sys.modules, and it
takes the app dir back off sys.path the moment the entrypoint script finishes.
resync() runs later than that — FoxhuntActivity.onCreate — so a bare
`import companion` there resolves only if some earlier screen already cached
it. From the second launch of a power session on, one always had: home's
prewarm, profiel and instellingen all import companion at their own module
level. The first launch after a boot or a deploy has nothing cached, and that
is exactly the launch resync() exists for, since only an unsynced profile ever
gets past the guard above the import.

So the test rebuilds the cold launch on the host: assets dir off sys.path,
companion evicted, and only what foxhunt.py imports at entrypoint time warm.
"""

import importlib.util
from pathlib import Path
import sys
import types
import unittest
from unittest.mock import MagicMock, patch


ASSETS = Path(__file__).parents[1] / "com.enigmeta.foxhunt" / "assets"

UNSYNCED = {
    "name": "Vera",
    "badge_id": "A4:CF:00:00:00:01",
    "head": "vos",
    "accs": ["bril", "strik"],
    "bg": 0,
    "synced": False,
}


def load_registrar():
    """Import registrar.py the way the badge does: app dir on sys.path for the
    duration of the entrypoint, gone again afterwards."""
    spec = importlib.util.spec_from_file_location(
        "registrar_under_test", ASSETS / "registrar.py"
    )
    module = importlib.util.module_from_spec(spec)
    stubs = {"lvgl": MagicMock(), "mpos": MagicMock()}
    sys.path.insert(0, str(ASSETS))
    try:
        with patch.dict(sys.modules, stubs):
            spec.loader.exec_module(module)
    finally:
        sys.path.remove(str(ASSETS))
    return module


def entrypoint_lazy():
    """foxhunt.lazy, in the shape the entrypoint defines it: put the app dir
    back for the duration of the import, then take it away again."""
    app_path = str(ASSETS)

    def lazy(name):
        m = sys.modules.get(name)
        if m is not None:
            return m
        sys.path.insert(0, app_path)
        try:
            return __import__(name)
        finally:
            sys.path.remove(app_path)

    return lazy


class ResyncColdLaunchTest(unittest.TestCase):
    def setUp(self):
        self.registrar = load_registrar()
        self.registrar.BASE_URL = "http://localhost:8787"
        self.sent = []
        self.registrar.REGISTRAR = types.SimpleNamespace(
            register=lambda *a: self.sent.append(a)
        )

    def cold_launch(self, profile):
        """Run resync() with only the entrypoint's own imports warm.

        Other test modules in this suite leave the assets dir on sys.path and
        companion in sys.modules, which is the very state that hides the bug —
        strip both for the duration.
        """
        store = types.ModuleType("store")
        store.profile = lambda: dict(profile) if profile else None
        foxhunt = types.ModuleType("foxhunt")
        foxhunt.lazy = entrypoint_lazy()

        warm = {
            "lvgl": MagicMock(),
            "mpos": MagicMock(),
            "store": store,
            "foxhunt": foxhunt,
            # what foxhunt.py imports at entrypoint time, minus the ones this
            # path never touches. companion is deliberately NOT here.
            "companion": None,
        }
        path = list(sys.path)
        try:
            with patch.dict(sys.modules, warm):
                del sys.modules["companion"]
                if str(ASSETS) in sys.path:
                    sys.path.remove(str(ASSETS))
                self.registrar.resync()
        finally:
            sys.path[:] = path

    def test_cold_launch_resyncs_an_unconfirmed_profile(self):
        self.cold_launch(UNSYNCED)
        self.assertEqual(len(self.sent), 1, "resync did not reach the transport")
        name, badge, code, _on_update = self.sent[0]
        self.assertEqual(name, "Vera")
        self.assertEqual(badge, "A4:CF:00:00:00:01")
        # The real companion.py, imported through lazy() with no help from a
        # warm sys.modules: head 1, bril + strik, backdrop 1.
        self.assertEqual(code, "H01A003C1")

    def test_a_confirmed_profile_still_sends_nothing(self):
        synced = dict(UNSYNCED, synced=True)
        self.cold_launch(synced)
        self.assertEqual(self.sent, [])

    def test_no_profile_still_sends_nothing(self):
        self.cold_launch(None)
        self.assertEqual(self.sent, [])


if __name__ == "__main__":
    unittest.main()
