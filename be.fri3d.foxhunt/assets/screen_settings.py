# screen_settings.py — placeholder for the instellingen page.
#
# The design (home.jsx PxSettings) sketches sound/vibration/brightness
# toggles, maatje + name edit rows, a LoRa switch and a HERSTEL action;
# for now only the badge strip is real. Build out the rows here later.

from mpos import Activity
import ui
import registrar

STRIP_BG = 0xEFE7D0


class SettingsActivity(Activity):
    def onCreate(self):
        s = ui.make_screen(ui.PAPER)
        ui.banner(s, "INSTELLINGEN", ui.GREEN)
        ui.label(
            s,
            "nog niets in te stellen...",
            0,
            108,
            ui.TEXT_MUTED,
            ui.font_small(),
            w=320,
            center=True,
        )
        strip = ui.panel(s, 6, 212, 308, 22, bg=STRIP_BG)
        ui.label(strip, "BADGE", 6, 3, ui.MYSTERY, ui.font_small())
        ui.label(strip, registrar.badge_id(), 52, 3, ui.INK, ui.font_small())
        self.setContentView(s)
