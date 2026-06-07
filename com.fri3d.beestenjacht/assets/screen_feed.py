# screen_feed.py — VOEREN: feed a caught creature a hapje.
#
# A stage with the creature + a VERZADIGD (fullness) meter, and a 3-food picker
# below (Bes / Noot / Eikel). Tap a hapje to feed it. The creature's favourite
# food grants extra band. Layout follows the design (detail.jsx PxFeed).

import lvgl as lv
from mpos import Activity
import ui
import art
import sound
import store
import pet
from creatures import by_id

_FOODS = (("food", "Bes", "bes"), ("nut", "Noot", "noot"), ("acorn", "Eikel", "eikel"))


class FeedActivity(Activity):
    def onCreate(self):
        self.fox_id = self.getIntent().extras.get("fox_id", 0)
        self.c = by_id(self.fox_id)
        self._bubble_timer = None

        s = ui.make_screen(0xDFEEBF)
        ui.banner(s, "Voeren " + self.c["naam"], ui.GREEN)

        # ── stage ────────────────────────────────────────────────────────
        stage = ui.panel(s, 8, 32, 304, 116, ui.SURFACE_TINT)
        sp = art.creature_panel(stage, self.c, 6)
        sp.align(lv.ALIGN.BOTTOM_LEFT, 16, -2)
        self.bubble = ui.label(stage, "", 8, 8, ui.INK, ui.font_label(), w=140)

        # VERZADIGD meter, top-right inside the stage
        ui.label(stage, "VERZADIGD", 188, 8, ui.GREEN_D, ui.font_small(), w=108, center=True)
        self.sat = []
        for i in range(5):
            c = ui.box(stage, 196 + i * 18, 28, 13, 16, ui.GREEN)
            c.set_style_border_width(2, 0)
            c.set_style_border_color(ui.hexc(ui.INK), 0)
            self.sat.append(c)
        ui.label(stage, "favoriet = +band", 188, 52, ui.TEXT_MUTED, ui.font_small(), w=108, center=True)

        # ── food picker ──────────────────────────────────────────────────
        fw = 97
        picker = ui.row(s, 8, 154, 3 * fw + 2 * 6, 50, gap=6)
        for ic, lab, food in _FOODS:
            fav = (food == self.c.get("favoriet"))
            p = ui.panel(picker, 0, 0, fw, 50, ui.CARD)
            art.icon(p, ic, 2).align(lv.ALIGN.TOP_MID, 0, 5)
            ui.label(p, lab, 0, 32, ui.INK, ui.font_small(), w=fw, center=True)
            if fav:
                art.draw_sprite(p, art.HEART, {"k": 0x7A1F12, "r": 0xE0463A}, 1).align(lv.ALIGN.TOP_RIGHT, -4, 4)
            ui.focusable(p, on_click=lambda f=food: self._feed(f))

        # ── hint ─────────────────────────────────────────────────────────
        hint = ui.panel(s, 8, 212, 304, 22, ui.CREAM)
        ui.label(hint, "tik een hapje om te voeren", 0, 3, ui.INK, ui.font_small(), w=304, center=True)

        self.setContentView(s)
        self._refresh()

    def onResume(self, screen):
        super().onResume(screen)
        self._refresh()

    def _refresh(self):
        st = store.beast_state(self.fox_id)
        if st is None:
            return
        self._set_meter(pet.segments(pet.fullness(st["hunger"])))

    def _set_meter(self, lit):
        for i, c in enumerate(self.sat):
            on = i < lit
            col = (ui.GOLD if i == lit - 1 else ui.GREEN) if on else ui.DORMANT
            c.set_style_bg_color(ui.hexc(col), 0)

    def _feed(self, food):
        st, ok, msg, is_fav = store.do_feed(self.fox_id, food)
        if st is None:
            return
        sound.play("caught" if is_fav else "tap" if ok else "error")
        self._set_meter(pet.segments(pet.fullness(st["hunger"])))
        self._flash(msg)

    def _flash(self, text):
        self.bubble.set_text(text)
        if self._bubble_timer:
            self._bubble_timer.delete()
        self._bubble_timer = lv.timer_create(self._clear, 1100, None)

    def _clear(self, t):
        t.delete()
        self._bubble_timer = None
        self.bubble.set_text("")
