# screen_games.py — the beestenschool mini-games: VLIEGEN, VANGEN, DANSEN.
#
# Every game is the same contract: the school gates and launches it with
# {fox_id, kost, fav}; the game pays the energy and banks the band through
# store.do_play the moment the session starts (backing out mid-game costs
# nothing extra and refunds nothing — the creature played, briefly). The end
# card shows the score and the creature's reaction, and offers another round
# only if the energy is really there.
#
# Controls use the badge where it fits: taps for VLIEGEN and VANGEN, the
# four-way joystick for DANSEN. No gesture needs explaining to a seven-year-old.

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
        self._grabbed = False
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

    def grab_keys(self, s, on_key):
        """Give the playfield itself the joystick/keyboard focus.

        The board pushes a key to whatever the default group has focused, so a
        game that wants to be steered has to BE that object. Added bare, never
        through ui.focusable() — a gold halo around the whole screen is exactly
        the wrong feedback. DANSEN also grabs the playfield because each stick
        direction is a dance move, not focus navigation.
        Released again in game_over()."""
        s.add_event_cb(on_key, lv.EVENT.KEY, None)
        g = lv.group_get_default()
        if g:
            g.add_obj(s)
            lv.group_focus_obj(s)
            self._grabbed = True

    # ── the end card ────────────────────────────────────────────────────
    def game_over(self, kop, retry=True):
        self._over = True
        leds.off()
        # Hand the joystick back BEFORE the card exists: with nothing focused,
        # the group focuses the first button the card registers. Keep the grab
        # and NOG EEN KEER / TERUG are unreachable without the touchscreen.
        if self._grabbed:
            lv.group_remove_obj(self.screen)
            self._grabbed = False
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
        if st is None or st["energy"] < store.play_cost(self.kost, st) * pet.SEG:
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

# Collision leniency, the oldest trick in the platformer book: the fox's box is
# 32x32 but the art doesn't fill it — ears, tail and paws leave transparent
# margin — so an honest box-vs-box test kills you for a hit that never looked
# like one. The player's hitbox shrinks by _GRACE on every side. It costs
# nothing when you were clearly going to crash and saves you when you weren't.
# The screen edges deliberately stay strict: there the sprite leaving the frame
# IS the visible signal, and a forgiving box would just clip the fox off-screen.
_GRACE = 5


class VliegActivity(GameActivity):
    TITLE = "VLIEGEN"
    BG = 0xCFE2AD
    TICK_MS = 50

    def build(self, s):
        s.add_flag(lv.obj.FLAG.CLICKABLE)
        s.add_event_cb(lambda e: self._flap(), lv.EVENT.CLICKED, None)
        self.grab_keys(s, self._key)
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
        self.bird = art.creature_panel(s, self.c, 2, flip_x=True)
        self._y = 110.0
        self._vy = 0.0
        # The round starts on the first tap, not on the first tick. Gravity,
        # the branches and the collision test all wait; only the sky keeps
        # drifting, so the held frame still looks alive. Without this a player
        # who is still reading the hint has already fallen out of the sky.
        self._flying = False
        self.bird.set_pos(_BIRD_X, int(self._y))
        self.obs = []  # {"top", "bot", "x", "passed"}
        self._spawn_t = 10
        ui.label(
            s,
            "tik om te fladderen - of stick omhoog",
            0,
            226,
            ui.TEXT_MUTED,
            ui.font_small(),
            w=320,
            center=True,
        )

    def _flap(self):
        if not self._over:
            self._flying = True
            self._vy = -6.5

    def _key(self, e):
        """Every "go" key flaps: joystick up and A on the badge, up / enter /
        space on the emulator keyboard. 0x20 is the space bar arriving as plain
        ASCII — the SDL keyboard passes printable keys straight through, and
        lv.KEY has no name for it."""
        if e.get_key() in (lv.KEY.UP, lv.KEY.ENTER, 0x20):
            self._flap()

    def _branch(self, s, y, h, cap):
        b = ui.box(s, 320, y, 26, max(2, h), _BRANCH)
        b.set_style_border_width(ui.BORDER, 0)
        b.set_style_border_color(ui.hexc(ui.INK), 0)
        # The end facing the gap keeps its ink cap — that edge is the thing the
        # player has to fly past, and it needs to be crisp. The other end runs
        # off the screen, where a cap would print a hard line across the branch
        # and make it read as a short plank floating there. `cap` says which.
        b.set_style_border_side(lv.BORDER_SIDE.LEFT | lv.BORDER_SIDE.RIGHT | cap, 0)
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
        if not self._flying:
            return
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
                    "top": self._branch(
                        s, 26, gap_y - _GAP // 2 - 26, lv.BORDER_SIDE.BOTTOM
                    ),
                    "bot": self._branch(
                        s,
                        gap_y + _GAP // 2,
                        240 - gap_y - _GAP // 2,
                        lv.BORDER_SIDE.TOP,
                    ),
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
            # collision: the fox's hitbox (its 32x32 box inset by _GRACE, so
            # x 55..77) vs the branch column outside the gap
            if x < _BIRD_X + 32 - _GRACE and x + 26 > _BIRD_X + _GRACE:
                if (
                    self._y + _GRACE < o["gap"] - _GAP // 2
                    or self._y + 32 - _GRACE > o["gap"] + _GAP // 2
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

# The playfield, named — the spawner does reachability maths off these numbers,
# so a hand-tuned literal moving out from under it would silently make the game
# unfair again.
_RUN = 4.0  # beast px per tick; it never stops, it only turns
_CX_MIN, _CX_MAX = 6.0, 282.0  # how far the beast can run
_BEAST_Y = 196  # top of the beast: where a falling hapje is caught
_ITEM_PX = 24  # a food icon at scale 3
_DROP_Y = 30  # where a hapje appears
_CATCH_Y = _BEAST_Y - _ITEM_PX  # item y at which its bottom meets the beast
_GONE_Y = 232  # past here the hapje is missed
# The catch window: cx may be anywhere in (item.x - 32, item.x + 24), so the
# beast aims at item.x - _AIM and a target cx wants a hapje at cx + _AIM.
_AIM = 4


class VangActivity(GameActivity):
    TITLE = "VANGEN"
    BG = 0xDFEEBF
    TICK_MS = 50

    def build(self, s):
        s.add_flag(lv.obj.FLAG.CLICKABLE)
        s.add_event_cb(lambda e: self._turn(), lv.EVENT.CLICKED, None)
        self.grab_keys(s, self._key)
        ui.box(s, 0, _HORIZON - 22, 320, 240 - _HORIZON + 22, _FIELD)
        for rows, pal, scale, x, base in _FIELD_ART:
            _scenery(s, rows, pal, scale, x, base - len(rows) * scale)
        ui.box(s, 0, _HORIZON, 320, 240 - _HORIZON, _GROUND)
        for rows, pal, scale, x, base in _CAMP_ART:
            _scenery(s, rows, pal, scale, x, base - len(rows) * scale)
        self.beast = art.creature_panel(s, self.c, 2)
        self._cx = 144.0
        self._dir = 1
        self.beast.set_pos(int(self._cx), _BEAST_Y)
        self.items = []  # {"w", "x", "y", "vy"}
        self._spawn_t = 10
        self._missed = 0
        self.hearts_box = ui.box(s, 8, 30, 66, 18)
        self._hearts()
        ui.label(
            s,
            "tik om te keren - of stuur met de stick",
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

    def _key(self, e):
        """Joystick left/right steer the beast. Both controls set the same
        _dir, so tapping and steering agree: a tap flips the direction, the
        stick names it outright."""
        if self._over:
            return
        k = e.get_key()
        if k == lv.KEY.LEFT:
            self._dir = -1
        elif k == lv.KEY.RIGHT:
            self._dir = 1

    def _due(self, it):
        """Ticks until `it` is catchable — its place in the queue the player
        has to work through, in order."""
        return (_CATCH_Y - it["y"]) / it["vy"]

    def _drop_x(self, vy):
        """Where a hapje falling at `vy` may appear: only somewhere the beast
        can still run to, given everything already in the air.

        The beast moves a fixed _RUN per tick and cannot stop, so its range is
        just speed times time — but time from WHERE. Measuring from where it
        stands now is not enough: two or three hapjes are usually falling at
        once, and a player who is off collecting the one that lands first has
        no way back for a second that was only reachable from a standstill.
        That is the version of this game that felt unfair.

        So the window chains: it hangs off the last hapje already due, and is
        as wide as the run the beast can make between that catch and this one.
        Serving them in the order they land is then always possible, which is
        the order a player plays in anyway. With an empty sky there is nothing
        to chain to and the beast's own position anchors it.

        The fall is measured to the FIRST catchable tick, not the last, so a
        drop at the very edge of the window still arrives with a little slack
        rather than demanding a frame-perfect turn."""
        fall = (_CATCH_Y - _DROP_Y) / vy
        if self.items:
            last = max(self.items, key=self._due)
            anchor, slack = last["x"] - _AIM, fall - max(0.0, self._due(last))
        else:
            anchor, slack = self._cx, fall
        reach = max(0.0, slack) * _RUN
        lo = max(_CX_MIN, anchor - reach) + _AIM
        hi = min(_CX_MAX, anchor + reach) + _AIM
        return random.randrange(int(lo), int(hi) + 1)

    def step(self):
        self._cx += _RUN * self._dir
        if self._cx < _CX_MIN:
            self._cx, self._dir = _CX_MIN, 1
        elif self._cx > _CX_MAX:
            self._cx, self._dir = _CX_MAX, -1
        self.beast.set_x(int(self._cx))

        self._spawn_t -= 1
        if self._spawn_t <= 0:
            self._spawn_t = max(16, 30 - self.score)
            vy = min(6.0, 2.5 + self.score * 0.08)
            food = random.choice(store.FOODS)
            w = art.icon(self.screen, food, 3)
            x = self._drop_x(vy)
            w.set_pos(x, _DROP_Y)
            self.items.append({"w": w, "x": x, "y": float(_DROP_Y), "vy": vy})
        for it in self.items[:]:
            it["y"] += it["vy"]
            it["w"].set_y(int(it["y"]))
            if (
                it["y"] + _ITEM_PX >= _BEAST_Y
                and it["x"] + _ITEM_PX > self._cx
                and it["x"] < self._cx + 32
            ):
                sound.play("tap")
                it["w"].delete()
                self.items.remove(it)
                self.set_score(self.score + 1)
            elif it["y"] > _GONE_Y:
                it["w"].delete()
                self.items.remove(it)
                self._missed += 1
                self._hearts()
                sound.play("error")
                if self._missed >= 3:
                    self.game_over("OEPS!")
                    return


# ════ DANSEN — het beest doet pasjes voor, de speler doet ze na ══════════
# (dx, dy, colour), in joystick-direction order. The same index drives
# movement, sound and LEDs, so every cue agrees.
_DANCE_MOVES = (
    (-64, 0, 0xF08A7A),
    (0, -52, 0xF6D88A),
    (0, 52, 0x9ACE7A),
    (64, 0, 0xB8C8D6),
)
_DANCE_X = 136
_DANCE_Y = 104
_DANCE_LEAD_TICKS = 10  # one second to get ready before the first move
_DANCE_STEP_TICKS = 10  # one second per move: 600 ms posed, 400 ms centred
_WIN_ROUNDS = 8


class DansActivity(GameActivity):
    TITLE = "DANSEN"
    TICK_MS = 100

    def build(self, s):
        self.grab_keys(s, self._key)
        stage = ui.panel(s, 20, 32, 280, 190, ui.SURFACE_SOFT)
        # A quiet tiled floor makes the creature's four moves easy to read
        # without turning them back into Simon buttons.
        for row in range(3):
            for col in range(3):
                ui.box(
                    stage,
                    24 + col * 76,
                    20 + row * 54,
                    72,
                    50,
                    0xE8DFC8 if (row + col) % 2 else 0xF2EAD7,
                )
        self.hint_l = ui.label(
            stage,
            "kijk naar de pasjes",
            0,
            5,
            ui.MYSTERY,
            ui.font_small(),
            w=276,
            center=True,
        )
        self.beast = art.creature_panel(s, self.c, 3, animate=True)
        self.beast.set_pos(_DANCE_X, _DANCE_Y)
        self.seq = []
        self.state = "new"
        self.t = 0
        self.show_i = 0
        self.inp = 0
        self._dim_t = 0

    def _pose(self, i=None):
        if i is None:
            self.beast.set_pos(_DANCE_X, _DANCE_Y)
            leds.off()
            return
        dx, dy, colour = _DANCE_MOVES[i]
        self.beast.set_pos(_DANCE_X + dx, _DANCE_Y + dy)
        try:
            rgb = ((colour >> 16) & 0xFF, (colour >> 8) & 0xFF, colour & 0xFF)
            leds.write([rgb] * 5)
        except Exception:
            pass

    def _key(self, e):
        keys = {
            lv.KEY.LEFT: 0,
            lv.KEY.UP: 1,
            lv.KEY.DOWN: 2,
            lv.KEY.RIGHT: 3,
        }
        i = keys.get(e.get_key())
        if i is not None:
            # The badge repeats a held joystick direction after 400 ms. A
            # dance step is one deliberate tilt, so consume nothing else from
            # this input device until the stick has physically returned to
            # neutral. This also stops a direction held during the demo from
            # leaking into the player's turn.
            indev = lv.indev_active()
            if indev:
                indev.wait_release()
            self._press(i)

    def step(self):
        if self._dim_t:
            self._dim_t -= 1
            if self._dim_t == 0:
                self._pose()
        if self.state == "new":
            self.seq.append(random.randrange(4))
            self.show_i = 0
            self.t = 0
            self.state = "lead"
            self.hint_l.set_text("kijk naar de pasjes")
        elif self.state == "lead":
            self.t += 1
            if self.t >= _DANCE_LEAD_TICKS:
                self.state = "show"
                self.t = 0
        elif self.state == "show":
            ph = self.t % _DANCE_STEP_TICKS
            if ph == 0:
                self._pose(self.seq[self.show_i])
                sound.play("sim%d" % self.seq[self.show_i])
            elif ph == 6:
                self._pose()
            elif ph == _DANCE_STEP_TICKS - 1:
                self.show_i += 1
                if self.show_i >= len(self.seq):
                    self.state = "wait"
                    self.inp = 0
                    self.hint_l.set_text("doe ze na met de stick!")
            self.t += 1
        elif self.state == "pause":
            self.t += 1
            if self.t >= 8:
                self.state = "new"

    def _press(self, i):
        if self._over or self.state != "wait":
            return
        self._pose(i)
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
