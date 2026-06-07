# screen_hunt.py — classic ARDF. Silhouette + heart/bpm + 5-LED hot/cold.
#
# A timer polls the (faked) radio; strength -> bpm + LEDs (warmer = closer).
# There is NO automatic "found": RSSI can't tell you you've physically reached
# the box. The player walks up, reads the code off the device, and taps
# "VOER DE CODE IN" themselves.

import lvgl as lv
from mpos import Activity, Intent
import ui
import art
import leds
import sound
from creatures import by_id
from fox_radio import RADIO
from screen_code import CodeActivity


class HuntActivity(Activity):
    def onCreate(self):
        self.fox_id = self.getIntent().extras.get("fox_id", 0)
        self.c = by_id(self.fox_id)
        self.timer = None
        self._beat = False

        s = ui.make_screen(0xCFE2AD)
        rare = self.c["rarity"] != "norm"
        ui.banner(s, self.c["naam"], ui.TERRA, right=("zeldzaam" if rare else "gewoon"))

        # scan card with the silhouette + heartbeat
        card = ui.box(s, 6, 30, 308, 120, ui.SURFACE_SOFT, radius=2)
        card.set_style_border_width(2, 0)
        card.set_style_border_color(ui.hexc(ui.TERRA), 0)
        self.sil = art.creature_panel(card, self.c, 6, silhouette=True)
        self.sil.align(lv.ALIGN.CENTER, 0, -2)
        self.heart = art.draw_sprite(card, art.HEART, {"k": 0x7A1F12, "r": 0xE0463A}, 3)
        self.heart.align(lv.ALIGN.TOP_RIGHT, -54, 8)
        self.bpm = ui.label(card, "--", 244, 8, ui.TERRA, ui.font_title(), w=60)

        ui.label(
            s,
            "draai rond om te zoeken",
            6,
            154,
            ui.INK,
            ui.font_small(),
            w=308,
            center=True,
        )

        # 5-LED mirror (emulator + redundant on-badge): cells 52x16, gap 5
        self.mirror = []
        for i in range(5):
            seg = ui.box(s, 20 + i * 57, 172, 52, 16, 0x222222, radius=2)
            seg.set_style_border_width(2, 0)
            seg.set_style_border_color(ui.hexc(ui.INK), 0)
            self.mirror.append(seg)
        ui.label(s, "koud", 20, 190, ui.GREEN_D, ui.font_small())
        ui.label(s, "warm", 252, 190, ui.TERRA, ui.font_small(), w=42, center=True)

        # player-driven: tap when you've physically found the box & read its code
        btn = ui.box(s, 6, 208, 308, 26, ui.GREEN, radius=3)
        btn.set_style_border_width(2, 0)
        btn.set_style_border_color(ui.hexc(ui.INK), 0)
        bl = ui.label(
            btn, "VOER DE CODE IN", 0, 0, ui.CREAM, ui.font_label(), w=308, center=True
        )
        bl.align(lv.ALIGN.CENTER, 0, 0)
        ui.focusable(btn, on_click=self._enter_code)

        self.setContentView(s)

    def onResume(self, screen):
        super().onResume(screen)
        RADIO.start(self.fox_id)  # restart cold on every entry / return
        self.timer = lv.timer_create(self._tick, 250, None)

    def onPause(self, screen):
        super().onPause(screen)
        if self.timer:
            self.timer.delete()
            self.timer = None
        leds.off()

    def _tick(self, t):
        if not self.has_foreground():
            return
        r = RADIO.reading(self.fox_id)
        self.bpm.set_text(str(int(60 + r.strength * 100)))

        # heartbeat: nudge the heart up/down each tick so it visibly throbs
        self._beat = not self._beat
        self.heart.align(lv.ALIGN.TOP_RIGHT, -54, 6 if self._beat else 10)

        leds.show_level(r.level)  # physical LEDs (badge)
        cols = leds.colors_for_level(r.level)
        for i, seg in enumerate(self.mirror):
            rr, gg, bb = cols[i]
            seg.set_style_bg_color(ui.hexc((rr << 16) | (gg << 8) | bb), 0)

    def _enter_code(self):
        if self.timer:
            self.timer.delete()
            self.timer = None
        leds.off()
        sound.play("tap")
        self.startActivity(
            Intent(activity_class=CodeActivity, extras={"fox_id": self.fox_id})
        )
