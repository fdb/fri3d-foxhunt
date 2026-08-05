# screen_starter.py — the startbeest reveal, onboarding's payoff moment.
#
# Registration minted one base-tier creature server-side (deterministic per
# badge — GAME_DESIGN.md, "The startbeest"); reg_send has already stored it
# locally before opening this. States rebuilt in place (the reg_send
# pattern): a veiled silhouette first — "er wacht iemand op je" — then the
# reveal, framed the way the design asks: the creature chose YOU. The calm
# card copies the win screen's geometry, so the two payoffs rhyme.
#
# The reveal flows into a GUIDED FIRST FEEDING — the whole tutorial is this
# one taught tap (GAME_DESIGN.md, "The first gatherer experience"): the
# pantry was pre-seeded, the player picks a hapje, the beest eats. Real
# mechanics, not a mock — store.do_feed spends the pantry and pays energie.

import lvgl as lv
from mpos import Activity
import ui
import art
import sound
import store
from creatures import by_id

BG = 0x20301C
TEXT_SOFT = 0xBCD0A4
GOLD_INK = 0x3A2A0C


class StarterActivity(Activity):
    def onCreate(self):
        self.fox_id = self.getIntent().extras.get("fox_id", 0)
        self.c = by_id(self.fox_id) or by_id(0)
        self.screen = ui.make_screen(BG)
        self.setContentView(self.screen)
        self._build_mystery()

    # ---- shared chrome ----------------------------------------------------
    def _card(self, s, silhouette):
        panel = ui.box(s, 114, 36, 92, 92, ui.SURFACE_SOFT, radius=2)
        panel.set_style_border_width(3, 0)
        border = ui.GREEN_D if silhouette else ui.GOLD
        panel.set_style_border_color(ui.hexc(border), 0)
        sp = art.creature_panel(
            panel, self.c, 5, silhouette=silhouette, animate=not silhouette
        )
        sp.align(lv.ALIGN.CENTER, 0, 0)
        return panel

    def _button(self, s, text, cb):
        # same margins as the win screen: room under it for the focus halo
        btn = ui.box(s, 84, 202, 152, 26, ui.GOLD, radius=3)
        btn.set_style_border_width(2, 0)
        btn.set_style_border_color(ui.hexc(ui.INK), 0)
        bl = ui.label(btn, text, 0, 0, GOLD_INK, ui.font_title(), w=152, center=True)
        bl.align(lv.ALIGN.CENTER, 0, 0)
        ui.focusable(btn, on_click=cb)

    # ---- state: mystery ---------------------------------------------------
    def _build_mystery(self):
        s = self.screen
        s.clean()
        ui.label(s, "SSST...", 0, 10, ui.GOLD, ui.font_title(), w=320, center=True)
        self._card(s, silhouette=True)
        ui.label(
            s,
            "Er wacht iemand op je!",
            0,
            140,
            ui.CREAM,
            ui.font_title(),
            w=320,
            center=True,
        )
        ui.label(
            s,
            "Een beest uit het bos is je gevolgd...",
            0,
            166,
            TEXT_SOFT,
            ui.font_small(),
            w=320,
            center=True,
        )
        self._button(s, "WIE IS DAT?", self._reveal)

    # ---- state: reveal ----------------------------------------------------
    def _reveal(self):
        s = self.screen
        s.clean()
        sound.play("caught")
        # sparks flank the card, clear of the 136-180 text band
        for x, y, sc in (
            (20, 44, 2),
            (286, 38, 3),
            (40, 90, 3),
            (270, 96, 2),
        ):
            art.icon(s, "spark", sc).set_pos(x, y)
        ui.label(
            s,
            "+ JOUW STARTBEEST +",
            0,
            10,
            ui.GOLD,
            ui.font_small(),
            w=320,
            center=True,
        )
        self._card(s, silhouette=False)
        ui.label(
            s,
            "%s heeft jou gekozen!" % self.c["naam"],
            0,
            140,
            ui.CREAM,
            ui.font_title(),
            w=320,
            center=True,
        )
        ui.label(
            s,
            "Zorg er goed voor - geef het hapjes en speel!",
            0,
            166,
            TEXT_SOFT,
            ui.font_small(),
            w=320,
            center=True,
        )
        self._button(s, "GEEF EEN HAPJE", self._build_feed)

    # ---- state: the guided first feeding ----------------------------------
    def _build_feed(self):
        s = self.screen
        s.clean()
        sound.play("tap")
        ui.label(
            s, "+ EERSTE HAPJE +", 0, 10, ui.GOLD, ui.font_small(), w=320, center=True
        )
        self._card(s, silhouette=False)
        ui.label(
            s,
            "Waar heeft %s zin in?" % self.c["naam"],
            0,
            136,
            ui.CREAM,
            ui.font_label(),
            w=320,
            center=True,
        )
        v = store.voorraad()
        fw = 92
        row = ui.row(s, 14, 158, 3 * fw + 2 * 8, 38, gap=8)
        for food, lab in (("bes", "Bes"), ("noot", "Noot"), ("eikel", "Eikel")):
            fav = food == self.c.get("favoriet")
            p = ui.panel(
                row, 0, 0, fw, 38, ui.CARD, border=(ui.GOLD if fav else ui.BORDER_REST)
            )
            art.icon(p, food, 2).set_pos(8, 10)
            ui.label(
                p, "%s x%d" % (lab, v.get(food, 0)), 32, 12, ui.INK, ui.font_small()
            )
            ui.focusable(
                p, on_click=lambda f=food: self._first_feed(f), focus_border=True
            )

    def _first_feed(self, food):
        st, ok, msg, is_fav = store.do_feed(self.fox_id, food)
        sound.play("caught" if is_fav else "tap" if ok else "error")
        self._build_fed(ok, msg, is_fav)

    def _build_fed(self, ok, msg, is_fav):
        s = self.screen
        s.clean()
        for x, y, sc in ((24, 46, 2), (282, 44, 2)):
            art.icon(s, "spark", sc).set_pos(x, y)
        ui.label(
            s, "+ SMAKELIJK +", 0, 10, ui.GOLD, ui.font_small(), w=320, center=True
        )
        self._card(s, silhouette=False)
        kop = "%s %s" % (self.c["naam"], "smikkelt!" if ok else "zit al vol!")
        ui.label(s, kop, 0, 138, ui.CREAM, ui.font_title(), w=320, center=True)
        if ok:
            ui.label(
                s,
                msg,
                0,
                162,
                ui.GOLD if is_fav else TEXT_SOFT,
                ui.font_small(),
                w=320,
                center=True,
            )
        ui.label(
            s,
            "hapjes vind je met plukken - band groeit door spelen",
            0,
            180,
            TEXT_SOFT,
            ui.font_small(),
            w=320,
            center=True,
        )
        self._button(s, "VERDER", self._done)

    def _done(self):
        sound.play("tap")
        self.setResult("done")
        self.finish()
