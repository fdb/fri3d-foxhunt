# screen_win.py — the "Gevangen!" payoff. One button: back to Home.

import lvgl as lv
import mpos.ui
from mpos import Activity
import ui
import art
from creatures import by_id


class WinActivity(Activity):
    def onCreate(self):
        self.fox_id = self.getIntent().extras.get("fox_id", 0)
        c = by_id(self.fox_id)
        leg = c["rarity"] == "leg"

        s = ui.make_screen(0x20301C)
        if leg:
            ui.label(s, "* LEGENDARISCH *", 0, 44, ui.GOLD, ui.font_small(), w=320, center=True)

        panel = ui.box(s, 114, 66, 92, 92, 0xE9F1CF, radius=2)
        panel.set_style_border_width(3, 0)
        panel.set_style_border_color(ui.hexc(ui.GOLD if leg else ui.GREEN_D), 0)
        sp = art.creature_panel(panel, c, 5)
        sp.align(lv.ALIGN.CENTER, 0, 0)

        ui.label(s, c["naam"], 0, 166, ui.CREAM, ui.font_title(), w=320, center=True)
        ui.label(s, "toegevoegd aan je boek!", 0, 192, 0xBCD0A4, ui.font_small(), w=320, center=True)

        btn = ui.box(s, 100, 210, 120, 26, ui.GOLD, radius=3)
        btn.set_style_border_width(2, 0)
        btn.set_style_border_color(ui.hexc(ui.INK), 0)
        bl = ui.label(btn, "VERDER", 0, 0, 0x3A2A0C, ui.font_title(), w=120, center=True)
        bl.align(lv.ALIGN.CENTER, 0, 0)
        ui.focusable(btn, on_click=self.go_home)

        self.setContentView(s)

    def go_home(self):
        # Stack is home -> hunt -> code -> win; pop the three to land on home.
        for _ in range(3):
            mpos.ui.back_screen()
