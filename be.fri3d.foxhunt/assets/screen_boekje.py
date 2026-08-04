# screen_boekje.py — VRIENDENBOEKJE: one page per first-ever meeting.
#
# The permanent layer under the daily vonk: never decays, grows all weekend.
# Every kid knows the friend-book ritual — meetings as memories, never as
# "collecting people". Layout follows the design (verzamelen.jsx PxBoekje /
# PxBoekjeLeeg).

import lvgl as lv
from mpos import Activity
import ui
import art
import sound
import store
import companion

_AVATAR_BG = 0xCFE0EA
_CELL_W, _CELL_H, _GAP = 99, 60, 5


class BoekjeActivity(Activity):
    def onCreate(self):
        vrienden = store.vrienden()
        s = ui.make_screen(ui.PAPER)
        n = len(vrienden)
        ui.banner(
            s,
            "VRIENDENBOEKJE",
            ui.GREEN,
            right="%d %s" % (n, "maatje" if n == 1 else "maatjes"),
        )
        if vrienden:
            self._grid(s, vrienden)
        else:
            self._empty(s)
        self.setContentView(s)

    def _grid(self, s, vrienden):
        grid = ui.row(s, 6, 34, 3 * _CELL_W + 2 * _GAP + 2, 200, gap=_GAP, wrap=True)
        grid.add_flag(lv.obj.FLAG.SCROLLABLE)
        grid.set_scroll_dir(lv.DIR.VER)
        for f in vrienden:
            card = ui.panel(grid, 0, 0, _CELL_W, _CELL_H, ui.CARD)
            head, accs, bg = companion.decode(f.get("code", ""))
            ava = ui.box(card, 3, 7, 40, 40, companion.BGS[bg])
            # 48px companion in a 40px opening: transparent margin falls off
            # the edges, the face stays centred (same crop as the home header)
            companion.draw(ava, head, accs, 3, x=-4, y=-4)
            ui.label(card, f.get("naam", "?"), 49, 12, ui.INK, ui.font_label())
            ui.label(card, f.get("dag", ""), 49, 30, ui.MYSTERY, ui.font_small())
            ui.focusable(card, focus_border=True)  # navigable, inert

    def _empty(self, s):
        p = ui.panel(s, 20, 48, 280, 140, ui.CARD)
        art.icon(p, "spark", 2).set_pos(16, 14)
        art.icon(p, "spark", 2).set_pos(248, 26)
        art.icon(p, "boek", 5).align(lv.ALIGN.TOP_MID, 0, 14)
        ui.label(
            p, "Nog niemand ontmoet", 0, 66, ui.INK, ui.font_title(), w=276, center=True
        )
        ui.label(
            p,
            "elke nieuwe snuffel geeft je",
            0,
            96,
            ui.MYSTERY,
            ui.font_small(),
            w=276,
            center=True,
        )
        ui.label(
            p,
            "een pagina in dit boekje",
            0,
            110,
            ui.MYSTERY,
            ui.font_small(),
            w=276,
            center=True,
        )
        btn = ui.panel(s, 20, 200, 280, 32, ui.GREEN)
        art.icon(btn, "snuf", 1).set_pos(70, 6)
        ui.label(
            btn, "GA SNUFFELEN", 0, 8, ui.CREAM, ui.font_label(), w=276, center=True
        )
        ui.focusable(btn, on_click=self._terug)

    def _terug(self):
        # the boekje is only reachable from the snuffelscherm, so back IS
        # "ga snuffelen" — no circular import needed
        sound.play("tap")
        self.finish()
