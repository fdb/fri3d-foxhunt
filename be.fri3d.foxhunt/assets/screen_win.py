# screen_win.py — the "Gevangen!" payoff. One button: back to Home.
#
# The fuss scales with the rarity. Base: a calm card, jingle from the code
# screen. Rare: the same card plus celebrate.Stardust — twinkling stars, a
# gold glint, a soft LED breathe. Legendary: the full maximalist fireworks
# (celebrate.Fireworks): rainbow halo, confetti, flashing title, bouncing
# beast, looping fanfare and a rainbow LED chase.
#
# A `pakket` extra makes it the ZELF GEVONDEN variant instead (GAME_DESIGN.md):
# the calm card for every rarity — a re-find is a visit, not a new legend —
# with the verzorgingspakket listed under a warmer title.

import lvgl as lv
import mpos.ui
from mpos import Activity
import ui
import art
from creatures import by_id
from celebrate import Fireworks, Stardust


class WinActivity(Activity):
    def onCreate(self):
        self.fox_id = self.getIntent().extras.get("fox_id", 0)
        self.pakket = self.getIntent().extras.get("pakket")  # zelf gevonden
        c = by_id(self.fox_id)
        leg = c["rarity"] == "leg" and not self.pakket
        self.fx = None

        s = ui.make_screen(0x140A2E if leg else 0x20301C)
        if leg:
            self.fx = Fireworks(s, c)
            self._verder_button(s, ui.GOLD, ui.INK)
        else:
            panel = self._calm_card(s, c)
            if c["rarity"] != "norm":
                self.fx = Stardust(s, panel)

        self.setContentView(s)

    def _calm_card(self, s, c):
        panel = ui.box(s, 114, 36, 92, 92, ui.SURFACE_SOFT, radius=2)
        panel.set_style_border_width(3, 0)
        panel.set_style_border_color(ui.hexc(ui.GOLD if self.pakket else ui.GREEN_D), 0)
        sp = art.creature_panel(panel, c, 5, animate=True)
        sp.align(lv.ALIGN.CENTER, 0, 0)

        ui.label(s, c["naam"], 0, 136, ui.CREAM, ui.font_title(), w=320, center=True)
        if self.pakket:
            ui.label(
                s,
                "zelf gevonden - blij je weer te zien!",
                0,
                162,
                0xBCD0A4,
                ui.font_small(),
                w=320,
                center=True,
            )
            regel = "  ".join("+%d %s" % (n, f) for f, n in sorted(self.pakket.items()))
            ui.label(
                s,
                "verzorgingspakket: " + regel,
                0,
                180,
                ui.GOLD,
                ui.font_small(),
                w=320,
                center=True,
            )
        else:
            ui.label(
                s,
                "toegevoegd aan je boek!",
                0,
                162,
                0xBCD0A4,
                ui.font_small(),
                w=320,
                center=True,
            )
        self._verder_button(s, ui.GOLD, ui.INK)
        return panel

    def _verder_button(self, s, bg, border):
        # y=202, not flush at the bottom: the focused button wears a 4px gold
        # halo outside its box, so it needs real screen margin under it.
        btn = ui.box(s, 100, 202, 120, 26, bg, radius=3)
        btn.set_style_border_width(2, 0)
        btn.set_style_border_color(ui.hexc(border), 0)
        bl = ui.label(
            btn, "VERDER", 0, 0, 0x3A2A0C, ui.font_title(), w=120, center=True
        )
        bl.align(lv.ALIGN.CENTER, 0, 0)
        ui.focusable(btn, on_click=self.go_home)

    def onResume(self, screen):
        super().onResume(screen)
        if self.fx:
            self.fx.start()

    def onPause(self, screen):
        super().onPause(screen)
        if self.fx:
            self.fx.stop()

    def go_home(self):
        # Stack is home -> hunt -> code -> win; pop the three to land on home.
        for _ in range(3):
            mpos.ui.back_screen()
