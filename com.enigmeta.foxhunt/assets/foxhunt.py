# foxhunt.py — app entry. FoxhuntActivity: the non-visual router.
#
# Loaded by MicroPythonOS via MANIFEST.JSON (classname FoxhuntActivity). The
# assets/ dir is on sys.path, so the flat `import ui`, `import art`, etc. work.
#
# It owns exactly one decision — registered or not — and immediately launches
# the matching screen. It never calls setContentView(): MicroPythonOS already
# showed the app icon while loading, so another branded screen here would only
# repeat it. Everything downstream may therefore assume store.profile() is not
# None; that invariant is this module's whole reason to exist.
#
# The one other thing it owns falls out of how the OS loads it: this is the
# ONLY module that runs fresh on every startapp, because MicroPythonOS evicts
# just the entrypoint and leaves every sibling cached in sys.modules. So a
# launch can only be recognised as a launch here — see _new_session().
#
# The router itself never enters the screen stack. It launches the visible
# activity for a result instead: registration reports "registered", while home
# reports "unregistered" after ALLES WISSEN. An ordinary Back reports nothing
# and therefore returns to the launcher.

import sys

from mpos import Activity, Intent
import store
import registrar
import telemetry

# The route targets are imported through lazy() below, not here: on the badge
# every module import pays ~0.25s of LittleFS open() overhead before its body
# even runs, and importing a flow module here pulls in every OTHER flow module
# it links to. Deferring them keeps each launch off the hook for screens it may
# never route to.

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
        _new_session()
        telemetry.boot()
        # Not a routing decision — the route below reads the profile, and this
        # never creates or removes one. It only settles a profile the server
        # never confirmed, which onboarding cannot come back to fix.
        registrar.resync()
        self._route()

    def _route(self):
        """Launch the one visible root screen for the current profile state."""
        if store.profile() is None:
            target = lazy("screens_onboarding").WelcomeActivity
        else:
            target = lazy("screens_system").HomeActivity
        self.startActivityForResult(Intent(activity_class=target), self._route_changed)

    def _route_changed(self, _result):
        # Only explicit state changes return a result. Backing out of Welcome
        # or Home returns no result, so Activity.finish() never calls us and the
        # player lands in the launcher. The stored profile, not the result text,
        # remains the verdict: both registration paths save before returning,
        # and ALLES WISSEN clears before returning.
        self._route()
