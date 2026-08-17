# Shared loader for screens_hunt.py, which merged hunt/code/win/snuffel/
# pluk/visitor into one module for LittleFS block economy: every test of a
# hunt-group screen now loads the whole group, so the stub set is the union
# of the group's imports. Pass overrides to replace any stub.
import importlib.util
import sys
import types
from pathlib import Path
from unittest.mock import MagicMock, patch

ASSETS = Path(__file__).parents[1] / "com.enigmeta.foxhunt" / "assets"
sys.path.insert(0, str(ASSETS))  # the real creatures.py (pure data) loads


def load_screens_hunt(name="screens_hunt_under_test", **overrides):
    """Load screens_hunt.py against a full stub set. Returns (module, stubs);
    stubs is the dict actually injected, so tests can reach the mocks."""
    mpos = types.ModuleType("mpos")
    mpos.Activity = type("Activity", (), {})

    class Intent:
        def __init__(self, **kwargs):
            self.__dict__.update(kwargs)

    mpos.Intent = Intent
    mpos.ui = MagicMock()

    fox_radio = types.ModuleType("fox_radio")
    fox_radio.RADIO = MagicMock()
    fox_radio.rssi_to_bpm = MagicMock(return_value=60)

    pluk_radio = types.ModuleType("pluk_radio")
    pluk_radio.RADIO = MagicMock()
    pluk_radio.PLUK_LEVEL = 4
    pluk_radio.yield_for = MagicMock(return_value={})

    snuffel_link = types.ModuleType("snuffel_link")
    snuffel_link.LINK = MagicMock()

    celebrate = types.ModuleType("celebrate")
    celebrate.Fireworks = MagicMock()
    celebrate.Stardust = MagicMock()

    screens_care = types.ModuleType("screens_care")
    screens_care.BeastActivity = type("BeastActivity", (), {})
    screens_care.BoekjeActivity = type("BoekjeActivity", (), {})

    foxhunt = types.ModuleType("foxhunt")
    foxhunt.lazy = MagicMock(
        side_effect=lambda _name: types.SimpleNamespace(
            BeastActivity=screens_care.BeastActivity,
            BoekjeActivity=screens_care.BoekjeActivity,
        )
    )

    sound = MagicMock()  # also serves `import sound as leds`

    stubs = {
        "lvgl": MagicMock(),
        "mpos": mpos,
        "mpos.ui": mpos.ui,
        "ui": MagicMock(),
        "art": MagicMock(),
        "sound": sound,
        "store": MagicMock(),
        "companion": MagicMock(),
        "celebrate": celebrate,
        "fox_radio": fox_radio,
        "pluk_radio": pluk_radio,
        "snuffel_link": snuffel_link,
        "screens_care": screens_care,
        "foxhunt": foxhunt,
    }
    stubs.update(overrides)

    spec = importlib.util.spec_from_file_location(name, ASSETS / "screens_hunt.py")
    module = importlib.util.module_from_spec(spec)
    with patch.dict(sys.modules, stubs):
        spec.loader.exec_module(module)
    return module, stubs
