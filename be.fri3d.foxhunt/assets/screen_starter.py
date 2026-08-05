# screen_starter.py — the startbeest reveal, onboarding's payoff moment.
#
# Registration minted one base-tier creature server-side (deterministic per
# badge — GAME_DESIGN.md, "The startbeest"); reg_send has already stored it
# locally before opening this. So this screen holds no game logic at all: it
# only performs the introduction. Two states rebuilt in place (the reg_send
# pattern): a veiled silhouette first — "er wacht iemand op je" — then the
# reveal, framed the way the design asks: the creature chose YOU. The calm
# card copies the win screen's geometry, so the two payoffs rhyme.

import lvgl as lv
from mpos import Activity
import ui
import art
import sound
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
        self._button(s, "VERDER", self._done)

    def _done(self):
        sound.play("tap")
        self.setResult("done")
        self.finish()
