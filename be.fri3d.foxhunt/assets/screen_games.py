# screen_games.py — the beestenschool mini-games: VLIEGEN, VANGEN, SIMON.
#
# Every game is the same contract: the school gates and launches it with
# {fox_id, kost, fav}; the game pays the energy and banks the band through
# store.do_play the moment the session starts (backing out mid-game costs
# nothing extra and refunds nothing — the creature played, briefly). The end
# card shows the score and the creature's reaction, and offers another round
# only if the energy is really there.
#
# Controls are one-finger on purpose: tap to flap, tap to turn, tap a pad.
# No gesture needs explaining to a seven-year-old.

import random

import lvgl as lv
from mpos import Activity
import ui
import art
import leds
import sound
import store
import pet
from creatures import by_id


class GameActivity(Activity):
    """Shared scaffolding: banner + score, the play-session economy, the
    game-over card with NOG EEN KEER / TERUG. Subclasses implement build()
    and step()."""

    TITLE = "?"
    BG = ui.PAPER
    TICK_MS = 50

    def onCreate(self):
        x = self.getIntent().extras
        self.fox_id = x.get("fox_id", 0)
        self.kost = x.get("kost", 1)
        self.fav = x.get("fav", False)
        self.c = by_id(self.fox_id)
        self.timer = None
        self._over = False
        self.score = 0
        st, ok, self.pet_msg = store.do_play(self.fox_id, self.kost, self.fav)
        self.naam = (st or {}).get("bijnaam") or self.c["naam"]
        self.screen = ui.make_screen(self.BG)
        self._build_chrome()
        self.build(self.screen)
        self.setContentView(self.screen)
        if not ok:
            # the school gates on energy, but state may have decayed between
            # screens — refuse gracefully instead of playing on credit
            self.game_over(self.pet_msg, retry=False)

    def _build_chrome(self):
        ui.banner(self.screen, self.TITLE, ui.GREEN)
        self.right_l = ui.label(
            self.screen, "", 240, 8, ui.CREAM, ui.font_small(), w=72, center=True
        )
        self.set_score(0)

    def set_score(self, n):
        self.score = n
        self.right_l.set_text("score %d" % n)

    def onResume(self, screen):
        super().onResume(screen)
        self.timer = lv.timer_create(self._tick, self.TICK_MS, None)

    def onPause(self, screen):
        super().onPause(screen)
        if self.timer:
            self.timer.delete()
            self.timer = None
        leds.off()

    def _tick(self, t):
        if self.has_foreground() and not self._over:
            self.step()

    # ── the end card ────────────────────────────────────────────────────
    def game_over(self, kop, retry=True):
        self._over = True
        leds.off()
        card = ui.panel(self.screen, 30, 46, 260, 138, ui.CARD)
        ui.label(card, kop, 0, 8, ui.TERRA, ui.font_title(), w=256, center=True)
        ui.label(
            card,
            "score: %d" % self.score,
            0,
            40,
            ui.INK,
            ui.font_label(),
            w=256,
            center=True,
        )
        ui.label(
            card,
            "%s: %s" % (self.naam, self.pet_msg),
            0,
            60,
            ui.TEXT_MUTED,
            ui.font_small(),
            w=256,
            center=True,
        )
        self.note_l = ui.label(
            card, "", 0, 76, ui.TERRA_D, ui.font_small(), w=256, center=True
        )
        bw = 122
        again = ui.panel(card, 4, 96, bw, 30, ui.GREEN if retry else ui.DORMANT)
        ui.label(
            again,
            "NOG EEN KEER",
            0,
            7,
            ui.CREAM if retry else ui.MYSTERY,
            ui.font_label(),
            w=bw - 4,
            center=True,
        )
        if retry:
            ui.focusable(again, on_click=self._again)
        terug = ui.panel(card, 4 + bw + 6, 96, bw, 30, ui.CARD)
        ui.label(terug, "TERUG", 0, 7, ui.INK, ui.font_label(), w=bw - 4, center=True)
        ui.focusable(terug, on_click=self._terug)

    def _again(self):
        st = store.beast_state(self.fox_id)
        if st is None or st["energy"] < self.kost * pet.SEG:
            sound.play("error")
            self.note_l.set_text("te moe - eerst een hapje!")
            return
        sound.play("tap")
        st, ok, self.pet_msg = store.do_play(self.fox_id, self.kost, self.fav)
        self._over = False
        self.screen.clean()
        self._build_chrome()
        self.build(self.screen)

    def _terug(self):
        sound.play("tap")
        self.finish()


# ── scenery ──────────────────────────────────────────────────────────────
# Backdrops are built before the player and before any obstacle, so LVGL's
# creation order alone keeps them behind everything — no z-index juggling.
def _scenery(parent, rows, pal, scale, x, y):
    """One backdrop sprite. Scenery must never be tappable: the whole game
    screen carries the tap-to-flap / tap-to-turn handler, and a clickable
    child eats the event before it reaches the screen (same reason ui.box
    drops the flag)."""
    w = art.draw_sprite(parent, rows, pal, scale)
    w.set_pos(x, y)
    w.remove_flag(lv.obj.FLAG.CLICKABLE)
    return w


# ════ VLIEGEN — flappy: tik om te fladderen, ontwijk de takken ═══════════
_BRANCH = 0x8A5F2C
_GAP = 84  # opening between branch pair
_BIRD_X = 50

# Parallax layers: (grid, palette, scale, px per tick). Depth is signalled on
# three channels at once — far clouds are smaller, paler and slower — because
# speed alone is barely legible on a 320px screen. The branches scroll at 3.0,
# so even the fastest cloud stays visibly behind the play field.
_SKY = (
    (art.PUFF, {"w": 0xE7F0CE, "s": 0xDCE8BC}, 2, 0.5),
    (art.PUFF, {"w": 0xE7F0CE, "s": 0xDCE8BC}, 2, 0.5),
    (art.CLOUD, {"w": 0xECF2D6, "s": 0xDFE9C2}, 2, 1.0),
    (art.CLOUD, {"w": 0xFFF7E6, "s": 0xEDF3D8}, 3, 1.6),
    (art.CLOUD, {"w": 0xFFF7E6, "s": 0xEDF3D8}, 3, 1.6),
)
_SKY_TOP = 32  # clear of the 26px banner, which is drawn before the clouds
_SKY_BOT = 148


class VliegActivity(GameActivity):
    TITLE = "VLIEGEN"
    BG = 0xCFE2AD
    TICK_MS = 50

    def build(self, s):
        s.add_flag(lv.obj.FLAG.CLICKABLE)
        s.add_event_cb(lambda e: self._flap(), lv.EVENT.CLICKED, None)
        self.clouds = []
        for i, (rows, pal, scale, sp) in enumerate(_SKY):
            # seeded apart rather than at random, so a fresh round never starts
            # with every cloud stacked in one corner
            x = (i * 67 + random.randrange(0, 40)) % 320
            y = random.randrange(_SKY_TOP, _SKY_BOT)
            w = _scenery(s, rows, pal, scale, x, y)
            self.clouds.append(
                {"w": w, "x": float(x), "px": len(rows[0]) * scale, "sp": sp, "ix": x}
            )
        self.bird = art.creature_panel(s, self.c, 2)
        self._y = 110.0
        self._vy = 0.0
        self.bird.set_pos(_BIRD_X, int(self._y))
        self.obs = []  # {"top", "bot", "x", "passed"}
        self._spawn_t = 10
        ui.label(
            s,
            "tik om te fladderen",
            0,
            226,
            ui.TEXT_MUTED,
            ui.font_small(),
            w=320,
            center=True,
        )

    def _flap(self):
        if not self._over:
            self._vy = -6.5

    def _branch(self, s, y, h):
        b = ui.box(s, 320, y, 26, max(2, h), _BRANCH)
        b.set_style_border_width(ui.BORDER, 0)
        b.set_style_border_color(ui.hexc(ui.INK), 0)
        return b

    def _drift(self):
        """Scroll the parallax sky. The int-x guard matters: the slowest layer
        advances half a pixel per tick, so half its set_x calls would be a
        no-move that still costs LVGL an invalidate + redraw."""
        for c in self.clouds:
            c["x"] -= c["sp"]
            if c["x"] < -c["px"]:
                c["x"] = 320.0 + random.randrange(0, 48)
                c["w"].set_y(random.randrange(_SKY_TOP, _SKY_BOT))
            x = int(c["x"])
            if x != c["ix"]:
                c["ix"] = x
                c["w"].set_x(x)

    def step(self):
        s = self.screen
        self._drift()
        self._vy = min(8.0, self._vy + 0.9)
        self._y += self._vy
        if self._y < 26 or self._y > 240 - 32:
            sound.play("error")
            self.game_over("AUW!")
            return
        self.bird.set_pos(_BIRD_X, int(self._y))

        self._spawn_t -= 1
        if self._spawn_t <= 0:
            self._spawn_t = 46
            gap_y = random.randrange(92, 178)
            self.obs.append(
                {
                    "top": self._branch(s, 26, gap_y - _GAP // 2 - 26),
                    "bot": self._branch(s, gap_y + _GAP // 2, 240 - gap_y - _GAP // 2),
                    "x": 320.0,
                    "gap": gap_y,
                    "passed": False,
                }
            )
        for o in self.obs[:]:
            o["x"] -= 3.0
            x = int(o["x"])
            o["top"].set_x(x)
            o["bot"].set_x(x)
            if not o["passed"] and x + 26 < _BIRD_X:
                o["passed"] = True
                self.set_score(self.score + 1)
            if x < -30:
                o["top"].delete()
                o["bot"].delete()
                self.obs.remove(o)
                continue
            # collision: bird box (x 50..82) vs branch column outside the gap
            if x < _BIRD_X + 32 and x + 26 > _BIRD_X:
                if (
                    self._y < o["gap"] - _GAP // 2
                    or self._y + 32 > o["gap"] + _GAP // 2
                ):
                    sound.play("error")
                    self.game_over("AUW!")
                    return


# ════ VANGEN — het beest draaft heen en weer, tik om te keren ════════════
# The backdrop is a camp field in two planes. Nothing here moves: the beast
# runs along a fixed line, so a scrolling backdrop would only claim a motion
# that isn't happening. Depth comes from the horizon instead — the ground band
# starts where the far treeline stands, and the near row is drawn bigger and
# greener on top of it.
_FIELD = 0xD3E5AE  # far field, a shade under the screen's own bg
_GROUND = 0xC3D897  # near ground; its top edge IS the horizon line
_HORIZON = 198
_FAR = {"c": 0xBAD48F, "t": 0xC4B489}
_NEAR = {"c": 0x9CBE6C, "t": 0xA68E63}
_CANVAS = {"a": 0xE7D49B, "b": 0xBFA469}
# (grid, palette, scale, x, baseline) — y is derived so every tree stands ON
# its line instead of being hand-placed and floating a pixel.
_FIELD_ART = (
    (art.PINE, _FAR, 2, 26, _HORIZON),
    (art.TREE, _FAR, 2, 100, _HORIZON),
    (art.PINE, _FAR, 2, 176, _HORIZON),
    (art.TREE, _FAR, 2, 250, _HORIZON),
)
_CAMP_ART = (
    (art.TREE, _NEAR, 3, 2, 226),
    (art.TENT, _CANVAS, 3, 104, 226),
    (art.PINE, _NEAR, 3, 286, 226),
)


class VangActivity(GameActivity):
    TITLE = "VANGEN"
    BG = 0xDFEEBF
    TICK_MS = 50

    def build(self, s):
        s.add_flag(lv.obj.FLAG.CLICKABLE)
        s.add_event_cb(lambda e: self._turn(), lv.EVENT.CLICKED, None)
        ui.box(s, 0, _HORIZON - 22, 320, 240 - _HORIZON + 22, _FIELD)
        for rows, pal, scale, x, base in _FIELD_ART:
            _scenery(s, rows, pal, scale, x, base - len(rows) * scale)
        ui.box(s, 0, _HORIZON, 320, 240 - _HORIZON, _GROUND)
        for rows, pal, scale, x, base in _CAMP_ART:
            _scenery(s, rows, pal, scale, x, base - len(rows) * scale)
        self.beast = art.creature_panel(s, self.c, 2)
        self._cx = 144.0
        self._dir = 1
        self.beast.set_pos(int(self._cx), 196)
        self.items = []  # {"w", "x", "y", "vy"}
        self._spawn_t = 10
        self._missed = 0
        self.hearts_box = ui.box(s, 8, 30, 66, 18)
        self._hearts()
        ui.label(
            s,
            "tik om te keren",
            0,
            226,
            ui.TEXT_MUTED,
            ui.font_small(),
            w=320,
            center=True,
        )

    def _hearts(self):
        self.hearts_box.clean()
        for i in range(3):
            pal = (
                {"k": 0x7A1F12, "r": 0xE0463A}
                if i < 3 - self._missed
                else {"k": 0xB0A07E, "r": 0xECE0C2}
            )
            art.draw_sprite(self.hearts_box, art.HEART, pal, 2).set_pos(i * 22, 0)

    def _turn(self):
        if not self._over:
            self._dir = -self._dir

    def step(self):
        self._cx += 4.0 * self._dir
        if self._cx < 6:
            self._cx, self._dir = 6.0, 1
        elif self._cx > 282:
            self._cx, self._dir = 282.0, -1
        self.beast.set_x(int(self._cx))

        self._spawn_t -= 1
        if self._spawn_t <= 0:
            self._spawn_t = max(16, 30 - self.score)
            food = random.choice(store.FOODS)
            w = art.icon(self.screen, food, 3)
            x = random.randrange(10, 286)
            w.set_pos(x, 30)
            self.items.append(
                {"w": w, "x": x, "y": 30.0, "vy": min(6.0, 2.5 + self.score * 0.08)}
            )
        for it in self.items[:]:
            it["y"] += it["vy"]
            it["w"].set_y(int(it["y"]))
            if (
                it["y"] + 24 >= 196
                and it["x"] + 24 > self._cx
                and it["x"] < self._cx + 32
            ):
                sound.play("tap")
                it["w"].delete()
                self.items.remove(it)
                self.set_score(self.score + 1)
            elif it["y"] > 232:
                it["w"].delete()
                self.items.remove(it)
                self._missed += 1
                self._hearts()
                sound.play("error")
                if self._missed >= 3:
                    self.game_over("OEPS!")
                    return


# ════ SIMON — vier vlakken, volg de volgorde (en de LEDs) ════════════════
# (base colour, flash colour) per pad, mirroring the simon icon's palette
_PADS = (
    (0xD6483A, 0xF08A7A),
    (0xE8B23A, 0xF6D88A),
    (0x5A9A3C, 0x9ACE7A),
    (0x7F93A6, 0xB8C8D6),
)
_WIN_ROUNDS = 8


class SimonActivity(GameActivity):
    TITLE = "SIMON"
    TICK_MS = 100

    def build(self, s):
        self.pads = []
        for i, (base, flash) in enumerate(_PADS):
            x = 20 + (i % 2) * 150
            y = 36 + (i // 2) * 100
            pad = ui.panel(s, x, y, 130, 92, base)
            ui.focusable(pad, on_click=lambda k=i: self._press(k), focus_border=True)
            self.pads.append(pad)
        self.seq = []
        self.state = "new"
        self.t = 0
        self.show_i = 0
        self.inp = 0
        self._dim_t = 0

    def _light(self, i, on):
        base, flash = _PADS[i]
        self.pads[i].set_style_bg_color(ui.hexc(flash if on else base), 0)
        try:
            if on:
                rgb = ((flash >> 16) & 0xFF, (flash >> 8) & 0xFF, flash & 0xFF)
                leds.write([rgb] * 5)
            else:
                leds.off()
        except Exception:
            pass

    def step(self):
        if self._dim_t:
            self._dim_t -= 1
            if self._dim_t == 0:
                for i in range(4):
                    self._light(i, False)
        if self.state == "new":
            self.seq.append(random.randrange(4))
            self.show_i = 0
            self.t = 0
            self.state = "show"
        elif self.state == "show":
            # 500 ms per step: 350 lit, 150 dark, then the next one
            ph = self.t % 5
            if ph == 0:
                self._light(self.seq[self.show_i], True)
                sound.play("sim%d" % self.seq[self.show_i])
            elif ph == 3:
                self._light(self.seq[self.show_i], False)
            elif ph == 4:
                self.show_i += 1
                if self.show_i >= len(self.seq):
                    self.state = "wait"
                    self.inp = 0
            self.t += 1
        elif self.state == "pause":
            self.t += 1
            if self.t >= 8:
                self.state = "new"

    def _press(self, i):
        if self._over or self.state != "wait":
            return
        self._light(i, True)
        self._dim_t = 2
        sound.play("sim%d" % i)
        if i != self.seq[self.inp]:
            sound.play("error")
            self.game_over("OEPS!")
            return
        self.inp += 1
        if self.inp >= len(self.seq):
            self.set_score(len(self.seq))
            if len(self.seq) >= _WIN_ROUNDS:
                sound.play("caught")
                self.game_over("SUPER!")
                return
            self.state = "pause"
            self.t = 0
