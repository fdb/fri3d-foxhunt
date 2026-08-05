# screen_uitleg.py — HOE SPEEL JE?: the core loop in three rows, in the
# player's own mode (GAME_DESIGN.md, Roles and navigation).
#
# One screen, two texts: a verzamelaar reads their three verbs and learns
# that jagers bring the new creatures; a jager reads the hunt first and
# learns that verzamelaars hold the food. Shown once when the home screen
# first opens (store flag), and always reachable from instellingen. The
# text changes when the mode does, because it is rebuilt on every open.

import lvgl as lv
from mpos import Activity
import ui
import art
import sound
import store

# (icon, scale, kop, tekst) — icon grids differ (pluk/snuf 16px, ball/ant
# 8px), so the scale normalises every icon to exactly 32px
_VERZAMELAAR = (
    ("pluk", 2, "PLUKKEN", "loop naar een wifi-plek en pluk het eten"),
    ("snuf", 2, "SNUFFELEN", "badge tegen badge - deel een picknick"),
    ("ball", 4, "SPELEN", "voer je beest en speel - zo groeit de band"),
)
_VERZAMELAAR_VOET = "jagers brengen nieuwe beesten het kamp binnen"
_JAGER = (
    ("ant", 4, "JAGEN", "volg het signaal naar de vos - vang het beest"),
    ("pluk", 2, "VERZAMELEN", "pluk eten en snuffel met andere spelers"),
    ("ball", 4, "SPELEN", "voer je beest en speel - zo groeit de band"),
)
_JAGER_VOET = "verzamelaars hebben het eten dat jouw beesten zoeken"


class UitlegActivity(Activity):
    def onCreate(self):
        s = ui.make_screen(ui.PAPER)
        p = store.profile() or {}
        jager = bool(p.get("hunter_id"))
        ui.banner(s, "HOE SPEEL JE?", ui.GREEN)

        rows = _JAGER if jager else _VERZAMELAAR
        for i, (icon, sc, kop, tekst) in enumerate(rows):
            row = ui.panel(s, 8, 32 + i * 44, 304, 40, ui.CARD)
            art.icon(row, icon, sc).align(lv.ALIGN.LEFT_MID, 6, 0)
            ui.label(row, kop, 46, 4, ui.INK, ui.font_label())
            ui.label(row, tekst, 46, 21, ui.TEXT_MUTED, ui.font_small(), w=252)

        voet = ui.panel(s, 8, 166, 304, 24, ui.CREAM)
        ui.label(
            voet,
            _JAGER_VOET if jager else _VERZAMELAAR_VOET,
            0,
            4,
            ui.INK,
            ui.font_small(),
            w=300,
            center=True,
        )

        btn = ui.box(s, 84, 202, 152, 26, ui.GOLD, radius=3)
        btn.set_style_border_width(2, 0)
        btn.set_style_border_color(ui.hexc(ui.INK), 0)
        bl = ui.label(
            btn, "AAN DE SLAG!", 0, 0, 0x3A2A0C, ui.font_title(), w=152, center=True
        )
        bl.align(lv.ALIGN.CENTER, 0, 0)
        ui.focusable(btn, on_click=self._done)

        self.setContentView(s)

    def _done(self):
        sound.play("tap")
        self.finish()
