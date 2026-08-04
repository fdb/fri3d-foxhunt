# foxhunt.py — app entry. FoxhuntActivity: the router, and nothing else.
#
# Loaded by MicroPythonOS via MANIFEST.JSON (classname FoxhuntActivity). The
# assets/ dir is on sys.path, so the flat `import ui`, `import art`, etc. work.
#
# It owns exactly one decision — registered or not — and shows a splash while
# it makes it. Everything downstream may therefore assume store.profile() is
# not None; that invariant is this module's whole reason to exist.
#
# The splash STAYS on the stack underneath what it launches, and that is what
# makes the routing reversible: mpos has a screen stack, not a nav graph, so an
# activity cannot pop itself out from under a child. The system back gesture
# pops the child, this activity resumes, and decides again — see onResume.

import lvgl as lv
from mpos import Activity, Intent
import ui
import art
import store
from creatures import by_id
from screen_home import HomeActivity
from screen_welcome import WelcomeActivity

_SPLASH_SCALE = 8  # 16px art -> 128px


class FoxhuntActivity(Activity):
    def onCreate(self):
        self._onboarded = False
        self._booked = False
        s = ui.make_screen(ui.PAPER)
        art.creature_panel(s, by_id(0), _SPLASH_SCALE).align(lv.ALIGN.CENTER, 0, -8)
        ui.label(
            s, "VOSSENJACHT", 0, 180, ui.TERRA, ui.font_title(), w=320, center=True
        )
        self.setContentView(s)

    def onResume(self, screen):
        super().onResume(screen)
        # Reached once on launch (from setContentView) and again every time the
        # screen above closes. The route is read from stored state each time,
        # never from a result code: both onboarding routes save the profile
        # before they report success, so the profile IS the verdict.
        if store.profile() is None:
            if self._onboarded:
                # Back here still unregistered: the hunter walked out of the
                # welcome screen. Walk out of the app with them.
                self.finish()
                return
            self._onboarded = True
            self.startActivity(Intent(activity_class=WelcomeActivity))
        elif not self._booked:
            self._booked = True
            self.startActivity(Intent(activity_class=HomeActivity))
        else:
            self.finish()  # back out of the boek -> back to the launcher
