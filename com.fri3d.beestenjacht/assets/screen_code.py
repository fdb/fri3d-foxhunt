# screen_code.py — PIN keypad + creature reveal. Correct code -> WinActivity.

import lvgl as lv
from mpos import Activity, Intent
import ui
import art
import sound
import store
from creatures import by_id
from fox_radio import RADIO
from screen_win import WinActivity

KEYS = ["1", "2", "3", "4", "5", "6", "7", "8", "9", "<", "0", "OK"]


class CodeActivity(Activity):
    def onCreate(self):
        self.fox_id = self.getIntent().extras.get("fox_id", 0)
        self.c = by_id(self.fox_id)
        self.entry = ""

        s = ui.make_screen(0xDFEEBF)
        ui.banner(s, "VOER DE CODE IN", ui.GREEN)

        kx, ky, kw, kh, kg = 6, 34, 58, 45, 6
        for i, k in enumerate(KEYS):
            x = kx + (i % 3) * (kw + kg)
            y = ky + (i // 3) * (kh + kg)
            accent = (k == "OK")
            b = ui.box(s, x, y, kw, kh, ui.GREEN if accent else ui.CARD, radius=3)
            b.set_style_border_width(2, 0)
            b.set_style_border_color(ui.hexc(ui.INK), 0)
            kl = ui.label(b, k, 0, 0, ui.CREAM if accent else ui.INK, ui.font_title(), w=kw, center=True)
            kl.align(lv.ALIGN.CENTER, 0, 0)
            ui.focusable(b, on_click=lambda kk=k: self.press(kk))

        self.dots = ui.label(s, "____", 198, 40, ui.INK, ui.font_title(), w=116, center=True)
        self.rev = ui.box(s, 214, 80, 92, 92, ui.SURFACE_TINT, radius=2)
        self.rev.set_style_border_width(2, 0)
        self.rev.set_style_border_color(ui.hexc(ui.TERRA), 0)
        self._sprite = None
        self._draw_reveal()                       # starts as a full silhouette
        ui.label(s, "vul de code in", 198, 178, ui.TEXT_MUTED, ui.font_small(), w=116, center=True)

        self.setContentView(s)

    def _draw_reveal(self):
        # creature "fills in" top-down, a quarter per entered digit
        if self._sprite is not None:
            self._sprite.delete()
        self._sprite = art.creature_panel(self.rev, self.c, 4, reveal=len(self.entry) / 4.0)
        self._sprite.align(lv.ALIGN.CENTER, 0, 0)

    def press(self, k):
        sound.play("tap")
        if k == "<":
            self.entry = self.entry[:-1]
        elif k == "OK":
            return self.submit()
        elif len(self.entry) < 4:
            self.entry += k
        self.dots.set_text((self.entry + "____")[:4])
        self._draw_reveal()
        if len(self.entry) == 4:
            self.submit()

    def submit(self):
        if RADIO.verify_code(self.fox_id, self.entry):
            store.add_caught(self.fox_id)
            sound.play("caught")
            self.startActivity(Intent(activity_class=WinActivity, extras={"fox_id": self.fox_id}))
        else:
            sound.play("error")
            self.entry = ""
            self.dots.set_text("____")
            self._draw_reveal()
