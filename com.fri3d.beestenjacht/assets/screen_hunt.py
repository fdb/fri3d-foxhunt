# screen_hunt.py — classic ARDF. Silhouette + heart/bpm + 5-LED hot/cold.
# A timer polls the (faked) radio; strength -> bpm + LEDs; 'found' -> CodeActivity.

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
        RADIO.start(self.fox_id)
        self.timer = None
        self._beat = False

        s = ui.make_screen(0xCFE2AD)
        rare = self.c["rarity"] != "norm"
        ui.banner(s, self.c["naam"], ui.TERRA, right=("zeldzaam" if rare else "gewoon"), back=True)

        card = ui.box(s, 6, 30, 308, 146, 0xE9F1CF, radius=2)
        card.set_style_border_width(2, 0)
        card.set_style_border_color(ui.hexc(ui.TERRA), 0)
        self.sil = art.creature_sprite(card, self.c, 6, silhouette=True)
        self.sil.align(lv.ALIGN.CENTER, 0, -4)

        self.heart = art.draw_sprite(card, art.HEART, {"k": 0x7A1F12, "r": 0xE0463A}, 3)
        self.heart.align(lv.ALIGN.TOP_RIGHT, -52, 8)
        self.bpm = ui.label(card, "--", 246, 8, ui.TERRA, ui.font_title(), w=58)

        # 5-LED mirror (emulator + redundant on-badge): cells 52x16, gap 5
        self.mirror = []
        for i in range(5):
            seg = ui.box(s, 20 + i * 57, 180, 52, 16, 0x222222, radius=2)
            seg.set_style_border_width(2, 0)
            seg.set_style_border_color(ui.hexc(ui.INK), 0)
            self.mirror.append(seg)
        ui.label(s, "koud", 20, 198, ui.GREEN_D, ui.font_label())
        ui.label(s, "warm", 252, 198, ui.TERRA, ui.font_label(), w=42, center=True)

        ui.box(s, 6, 212, 308, 22, 0xFFFFFF)
        ui.label(s, "draai rond om te zoeken", 6, 216, ui.INK, ui.font_label(), w=308, center=True)

        self.setContentView(s)

    def onResume(self, screen):
        super().onResume(screen)
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
        self.heart.align(lv.ALIGN.TOP_RIGHT, -52, 6 if self._beat else 10)

        leds.show_level(r.level)                       # physical LEDs (badge)
        cols = leds.colors_for_level(r.level)
        for i, seg in enumerate(self.mirror):
            rr, gg, bb = cols[i]
            seg.set_style_bg_color(ui.hexc((rr << 16) | (gg << 8) | bb), 0)

        if r.found:
            self._found()

    def _found(self):
        if self.timer:
            self.timer.delete()
            self.timer = None
        leds.off()
        sound.play("warmer")
        self.startActivity(Intent(activity_class=CodeActivity, extras={"fox_id": self.fox_id}))
