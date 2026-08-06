# screen_feed.py — VOEREN: feed a caught creature a hapje FROM THE VOORRAAD.
#
# A stage with the creature + ENERGIE/HONGER bars, and a 3-food picker below
# showing what the pantry actually holds. Food is the energy leg of the
# chain — the favourite grants extra energie, band comes from spelen. An
# empty jar stays visible ('ga plukken') instead of vanishing. Layout
# follows the design (plukken.jsx PxVoer2).

import lvgl as lv
from mpos import Activity
import ui
import art
import sound
import store
import pet
from creatures import by_id

_FOODS = (("bes", "Bes"), ("noot", "Noot"), ("eikel", "Eikel"))


class FeedActivity(Activity):
    def onCreate(self):
        self.fox_id = self.getIntent().extras.get("fox_id", 0)
        self.c = by_id(self.fox_id)
        self._bubble_timer = None

        s = ui.make_screen(0xDFEEBF)
        ui.banner(s, "Voeren " + self.c["naam"], ui.GREEN)
        self.total_l = ui.label(
            s, "", 240, 8, ui.CREAM, ui.font_small(), w=72, center=True
        )

        # ── stage ────────────────────────────────────────────────────────
        stage = ui.panel(s, 8, 32, 304, 116, ui.SURFACE_TINT)
        sp = art.creature_panel(stage, self.c, 6)
        sp.align(lv.ALIGN.BOTTOM_LEFT, 16, -2)
        self.bubble = ui.label(stage, "", 8, 8, ui.INK, ui.font_label(), w=140)

        # ENERGIE / HONGER bars, top-right inside the stage
        self.energy_cells = self._bar(stage, 8, "ENERGIE")
        self.hunger_cells = self._bar(stage, 28, "HONGER")
        ui.label(
            stage,
            "voer vult energie",
            160,
            50,
            ui.TEXT_MUTED,
            ui.font_small(),
            w=136,
            center=True,
        )

        # ── voorraad picker ─────────────────────────────────────────────
        fw = 97
        picker = ui.row(s, 8, 154, 3 * fw + 2 * ui.GAP_M, 50, gap=ui.GAP_M)
        self.tiles = {}
        for food, lab in _FOODS:
            fav = food == self.c.get("favoriet")
            p = ui.panel(
                picker,
                0,
                0,
                fw,
                50,
                ui.CARD,
                border=(ui.GOLD if fav else ui.BORDER_REST),
            )
            ic = art.icon(p, food, 2)
            ic.set_pos(18, 9)
            cnt = ui.label(p, "", 40, 9, ui.INK, ui.font_title())
            if fav:
                art.draw_sprite(p, art.HEART, {"k": 0x7A1F12, "r": 0xE0463A}, 1).align(
                    lv.ALIGN.TOP_RIGHT, -4, 4
                )
            sub = ui.label(
                p, lab, 0, 32, ui.INK, ui.font_small(), w=fw - 4, center=True
            )
            ui.focusable(p, on_click=lambda f=food: self._feed(f), focus_border=True)
            self.tiles[food] = (p, ic, cnt, sub, lab)

        # ── hint ─────────────────────────────────────────────────────────
        hint = ui.panel(s, 8, 212, 304, 22, ui.CREAM)
        ui.label(
            hint,
            "favoriet = meer energie - band komt van spelen",
            0,
            3,
            ui.INK,
            ui.font_small(),
            w=304,
            center=True,
        )

        self.setContentView(s)
        self._refresh()

    def onResume(self, screen):
        super().onResume(screen)
        self._refresh()

    def _bar(self, parent, y, text):
        ui.label(parent, text, 160, y, ui.INK, ui.font_small())
        cells = []
        for i in range(5):
            c = ui.box(parent, 224 + i * 15, y, 12, 11, ui.DORMANT)
            c.set_style_border_width(ui.BORDER_THIN, 0)
            c.set_style_border_color(ui.hexc(ui.INK), 0)
            cells.append(c)
        return cells

    def _set_bar(self, cells, lit, color):
        for i, c in enumerate(cells):
            c.set_style_bg_color(ui.hexc(color if i < lit else ui.DORMANT), 0)

    def _refresh(self):
        st = store.beast_state(self.fox_id)
        if st is None:
            return
        self._set_bar(self.energy_cells, pet.energy_segments(st["energy"]), ui.GREEN)
        self._set_bar(self.hunger_cells, pet.segments(st["hunger"]), ui.TERRA)
        v = store.voorraad()
        self.total_l.set_text("%d voer" % store.voorraad_total())
        for food, (p, ic, cnt, sub, lab) in self.tiles.items():
            n = v.get(food, 0)
            cnt.set_text(str(n))
            p.set_style_bg_color(ui.hexc(ui.CARD if n else ui.DORMANT), 0)
            ic.set_style_opa(lv.OPA.COVER if n else 115, 0)
            sub.set_text(lab if n else "ga plukken")
            sub.set_style_text_color(ui.hexc(ui.INK if n else ui.MYSTERY), 0)

    def _feed(self, food):
        st, ok, msg, is_fav = store.do_feed(self.fox_id, food)
        if st is None:
            return
        sound.play("caught" if is_fav else "tap" if ok else "error")
        self._refresh()
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
