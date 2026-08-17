# foxhunt.py — app entry. FoxhuntActivity: the router, and nothing else.
#
# Loaded by MicroPythonOS via MANIFEST.JSON (classname FoxhuntActivity). The
# assets/ dir is on sys.path, so the flat `import ui`, `import art`, etc. work.
#
# It owns exactly one decision — registered or not — and shows a splash while
# it makes it. Everything downstream may therefore assume store.profile() is
# not None; that invariant is this module's whole reason to exist.
#
# The one other thing it owns falls out of how the OS loads it: this is the
# ONLY module that runs fresh on every startapp, because MicroPythonOS evicts
# just the entrypoint and leaves every sibling cached in sys.modules. So a
# launch can only be recognised as a launch here — see _new_session().
#
# The splash STAYS on the stack underneath what it launches, and that is what
# makes the routing reversible: mpos has a screen stack, not a nav graph, so an
# activity cannot pop itself out from under a child. The system back gesture
# pops the child, this activity resumes, and decides again — see onResume.

import sys

import lvgl as lv
from mpos import Activity, Intent
import ui
import art
import store
import registrar
import telemetry
from creatures import by_id

# The route targets are imported through lazy() below, not here: on the badge
# every module import pays ~0.25s of LittleFS open() overhead before its body
# even runs, and importing a flow module here pulls in every OTHER flow module
# it links to. Deferring them keeps the splash off the hook for screens this
# launch may never route to.

# The app dir sits on sys.path only while the OS runs this entrypoint script
# (AppManager restores the path the moment the script finishes), so capture it
# now: every deferred import must put it back for the duration of the import.
_APP_PATH = sys.path[0]


def lazy(name):
    """Import an app module after launch (tap handlers, prewarm, reroutes).

    Re-inserts the app dir around the import and removes it again, so the
    app's flat module names (ui, sound, store, ...) never linger at
    sys.path[0] where they could shadow an OS import.
    """
    m = sys.modules.get(name)
    if m is not None:
        return m
    sys.path.insert(0, _APP_PATH)
    try:
        return __import__(name)
    finally:
        sys.path.remove(_APP_PATH)


_SPLASH_SCALE = 8  # 16px art -> 128px


def _new_session():
    """Drop the state that must not outlive one run of the app.

    MicroPythonOS re-execs the entrypoint on every startapp but leaves the
    sibling modules in sys.modules, so a module global set during one launch is
    still set in the next — only this file runs fresh. That makes here the only
    place where "a new session starts" can be said at all, and doing it on the
    way IN rather than on the way out also covers the launches that follow a
    crash or a kill, where no teardown hook of ours would have run.

    Everything dropped here is debug or simulation state the badge deliberately
    keeps in RAM instead of on flash, which is exactly why store.reset_all — an
    allowlist over the preferences file — cannot reach any of it.

    sys.modules.get for the radio, not an import: a module that was never
    loaded holds no session to drop, and importing fox_radio to clear a
    singleton that does not exist yet would cost every cold start a LittleFS
    open (~0.25s) for nothing.
    """
    # Everything the debug screen can arm: the 1111 test code, and the cheats
    # (nooit_moe). All RAM-only on purpose, and none of it may
    # outlive the app that armed it — the next player gets a badge where the
    # code is dead and nothing is cheating, and an organiser who wants any of
    # it back is five deliberate taps on the badge id away.
    store.disable_debug_code()
    store.clear_debug_cheats()
    radio = sys.modules.get("fox_radio")
    if radio is not None:
        radio.RADIO.reset()


class FoxhuntActivity(Activity):
    def onCreate(self):
        self._onboarded = False
        self._booked = False
        _new_session()
        s = ui.make_screen(ui.PAPER)
        art.creature_panel(s, by_id(0), _SPLASH_SCALE).align(lv.ALIGN.CENTER, 0, -8)
        ui.label(
            s, "VOSSENJACHT", 0, 180, ui.TERRA, ui.font_title(), w=320, center=True
        )
        self.setContentView(s)
        telemetry.boot()
        # Not a routing decision — the route below reads the profile, and this
        # never creates or removes one. It only settles a profile the server
        # never confirmed, which onboarding cannot come back to fix.
        registrar.resync()

    def onResume(self, screen):
        super().onResume(screen)
        # Reached once on launch (from setContentView) and again every time the
        # screen above closes. The route is read from stored state each time,
        # never from a result code: both onboarding routes save the profile
        # before they report success, so the profile IS the verdict.
        #
        # Each latch means "I just sent them there and they came straight back",
        # which is the only case that should quit the app — so ENTERING either
        # screen clears the other one. Registration and ALLES WISSEN both flip
        # the verdict mid-run, and without the clears the second flip reads as
        # a bounce: wiping from instellingen would quit to the launcher instead
        # of offering to register again, and registering afterwards would quit
        # instead of opening the boek.
        if store.profile() is None:
            if self._onboarded:
                # Back here still unregistered: the hunter walked out of the
                # welcome screen. Walk out of the app with them.
                self.finish()
                return
            self._onboarded = True
            self._booked = False
            welcome = lazy("screens_onboarding").WelcomeActivity
            self.startActivity(Intent(activity_class=welcome))
        elif not self._booked:
            self._booked = True
            self._onboarded = False
            home = lazy("screens_system").HomeActivity
            self.startActivity(Intent(activity_class=home))
        else:
            self.finish()  # back out of the boek -> back to the launcher
