"""Deterministic emulator driver for scripts/capture_server_screens.sh.

This module is copied into MicroPythonOS's internal filesystem for one run.
It launches the real badge activities, arranges non-radio UI state, and asks
the emulator's own testing helper for RGB565 framebuffer captures.
"""

import random
import sys

import lvgl as lv
from mpos import Intent
from mpos.activity_navigator import ActivityNavigator
from mpos.ui import view
from mpos.ui.testing import capture_screenshot, wait_for_render

APP_ID = "com.enigmeta.foxhunt"
_FOX_ID = 0  # Vos: a base creature, used for every revealed creature shot.


class _Peer:
    def __init__(self):
        self.mac = "a4:cf:12:00:00:01"
        self.naam = "Sam"
        self.code = "H01A003C1"
        self.rssi = -43
        self.close = True


class _Spot:
    def __init__(self):
        self.bssid = "02:00:00:00:00:01"
        self.ssid = "fri3d-badge"
        self.rssi = -37
        self.level = 5


def _module(name):
    return sys.modules["foxhunt"].lazy(name)


def _launch(module_name, class_name, extras=None):
    view.remove_and_stop_all_activities()
    random.seed(2026)
    cls = getattr(_module(module_name), class_name)
    intent = Intent(activity_class=cls, extras=extras or {})
    intent.app_fullname = APP_ID
    ActivityNavigator.startActivity(intent)
    return view.screen_stack[-1][0]


def _hunter(on=True):
    store = _module("store")
    store.update_profile(hunter_id=42 if on else None, synced=True)


def _assert_spoiler_free():
    store = _module("store")
    creatures = _module("creatures")
    caught = store.caught_ids()
    assert caught, "screenshot fixture must include caught creatures"
    assert all(creatures.by_id(cid)["rarity"] == "norm" for cid in caught), (
        "screenshot fixture contains a rare or legendary creature"
    )
    assert _FOX_ID in store.zelf_ids(), "own-find badge fixture is missing"


def show(name):
    """Build one named public-site screenshot using synthetic local state."""
    _assert_spoiler_free()

    if name == "welkom":
        return _launch("screens_onboarding", "WelcomeActivity")
    if name in ("maatje-kop", "maatje-extra"):
        activity = _launch(
            "screens_onboarding", "CompanionActivity", {"name": "Robin"}
        )
        if name == "maatje-extra":
            activity._switch_tab(1)
        return activity
    if name == "ingeschreven":
        onboarding = _module("screens_onboarding")
        # The screenshot is a render fixture, never a registration request.
        onboarding.REGISTRAR.__class__.register = (
            lambda self, player, badge, code, callback: None
        )
        activity = _launch("screens_onboarding", "RegSendActivity")
        activity._stop_bar()
        activity._build_done({"hunter_id": 42, "bridge": "ok"})
        return activity

    if name == "boek":
        _hunter(True)
        return _launch("screens_system", "HomeActivity")
    if name == "oppad":
        _hunter(False)
        return _launch("screens_system", "HomeActivity")

    _hunter(True)
    if name == "jacht":
        return _launch("screens_hunt", "HuntActivity", {"fox_id": _FOX_ID})
    if name == "code":
        return _launch("screens_hunt", "CodeActivity", {"fox_id": _FOX_ID})
    if name == "gevangen":
        return _launch("screens_hunt", "WinActivity", {"fox_id": _FOX_ID})
    if name == "snuffelen":
        activity = _launch("screens_hunt", "SnuffelActivity")
        if activity.timer:
            activity.timer.delete()
            activity.timer = None
        _module("screens_hunt").LINK.stop()
        peer = _Peer()
        activity.rows_box.clean()
        activity._build_row(0, peer)
        activity._update_row(activity._rows[peer.mac], peer)
        activity.empty_l.add_flag(lv.obj.FLAG.HIDDEN)
        return activity
    if name == "vonk":
        return _launch(
            "screens_hunt",
            "VonkActivity",
            {
                "naam": "Sam",
                "code": "H01A003C1",
                "vonk": True,
                "new_friend": True,
                "dag": "2026-08-08",
                "food": "bes",
                "amount": 2,
                "geluk": None,
            },
        )
    if name in ("plukken", "oogst"):
        activity = _launch("screens_hunt", "PlukActivity")
        if activity.timer:
            activity.timer.delete()
            activity.timer = None
        _module("pluk_radio").RADIO.stop()
        if name == "plukken":
            activity._target = _Spot()
            activity._show(activity._target, 0)
        else:
            activity._harvest = {"bes": 2, "noot": 0, "eikel": 0}
            activity.screen.clean()
            activity._build_oogst(activity._harvest)
        return activity

    care = {
        "beest": ("BeastActivity", {"fox_id": _FOX_ID}),
        "voeren": ("FeedActivity", {"fox_id": _FOX_ID}),
        "dossier": ("DossierActivity", {"fox_id": _FOX_ID}),
        "school": ("SchoolActivity", {"fox_id": _FOX_ID}),
        "vliegen": (
            "VliegActivity",
            {"fox_id": _FOX_ID, "kost": 2, "fav": True},
        ),
        "vangen": (
            "VangActivity",
            {"fox_id": _FOX_ID, "kost": 1, "fav": False},
        ),
        "dansen": (
            "DansActivity",
            {"fox_id": _FOX_ID, "kost": 1, "fav": False},
        ),
        "vriendenboekje": ("BoekjeActivity", {}),
    }
    if name in care:
        class_name, extras = care[name]
        activity = _launch("screens_care", class_name, extras)
        # Freeze gameplay at a deliberate frame. Fixed random seeds alone are
        # not enough when a busy host can deliver a different number of timer
        # ticks during the shell driver's one-second render wait.
        if name in ("vliegen", "vangen", "dansen"):
            if activity.timer:
                activity.timer.delete()
                activity.timer = None
            if name == "vliegen":
                activity._flap()
                for _ in range(20):
                    activity.step()
            elif name == "vangen":
                for _ in range(12):
                    activity.step()
            else:
                activity.seq = [3]
                activity.state = "show"
                activity.show_i = 0
                activity.t = 0
                activity.step()
        return activity
    raise ValueError("unknown screenshot: " + name)


def shot(path):
    wait_for_render()
    capture_screenshot(path)
    print("CAPTURED " + path)
