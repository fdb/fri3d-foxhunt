# celebrate.py — the catch payoffs that move: Fireworks (leg) and Stardust
# (rare). Base catches stay a still card with the plain jingle.
#
# Fireworks is Peggle-blast energy for a "leg" rarity catch: a pulsing rainbow
# halo, falling confetti, twinkling sparkles, a bouncing beast, a flashing
# title, a looping fanfare, and a rainbow chase across the 5 physical LEDs.
# Stardust is deliberately a class below it: twinkling stars, a gold glint on
# the card, a soft gold LED breathe — special, not unhinged. Each is driven by
# one lv.timer; start()/stop() own its lifecycle so WinActivity just wires it
# into onResume/onPause (and the LEDs/buzzer no-op on desktop).

import lvgl as lv
import math
import random
import ui
import art
import sound
import leds

# Vivid 8-hue rainbow reused everywhere — bg wash, halo, confetti, title, LEDs.
RAINBOW = [
    0xE83B2E,  # red
    0xF0791B,  # orange
    0xF4C20D,  # yellow
    0x57C04A,  # green
    0x39A0D8,  # cyan
    0x4156C7,  # blue
    0x9B3FC9,  # violet
    0xE0379E,  # magenta
]
# Bright-only subset for the flashing title, so it never dips to a dark hue.
_BRIGHT = [0xFFF7E6, 0xF4C20D, 0x57E0C0, 0xFF7BD5, 0x7CC8FF, 0xFFFFFF]
PRAISE = ["ONGELOOFLIJK!", "JE BENT EEN LEGENDE", "SPECTACULAIR!", "WAT EEN VANGST!"]

# 5x5 diamond sparkle, drawn white and recoloured per twinkle.
_STAR = [
    "..w..",
    ".www.",
    "wwwww",
    ".www.",
    "..w..",
]

_CX, _CY = 160, 104  # creature centre — the halo radiates from here

_CONFETTI = 22
_TICK_MS = 80
_FANFARE_TICKS = 46  # ~3.7s — re-trigger the loop a touch before it ends


def _rgb(c):
    return (c >> 16) & 0xFF, (c >> 8) & 0xFF, c & 0xFF


def _dim(c, t):
    """Scale a colour toward black by factor t (0..1) — the dark bg wash."""
    r, g, b = _rgb(c)
    return (int(r * t) << 16) | (int(g * t) << 8) | int(b * t)


class Fireworks:
    """Builds every celebration widget on `screen` and animates them on a timer.
    The caller adds its own foreground widgets (the VERDER button) AFTER
    constructing this, so they stack on top of the confetti."""

    def __init__(self, screen, creature):
        self.s = screen
        self.c = creature
        self.timer = None
        self.frame = 0
        self._leds = False  # set in start(): True only when real NeoPixels answered
        self._build()

    # ── build: bottom-to-top so z-order is halo < beast < text < confetti ──
    def _build(self):
        s = self.s

        # 1. concentric rainbow halo (the radiating "rays" / bullseye).
        self.rings = []
        for i in range(7):
            size = 204 - i * 22
            ring = ui.box(
                s,
                _CX - size // 2,
                _CY - size // 2,
                size,
                size,
                RAINBOW[i],
                radius=size // 2,
            )
            self.rings.append(ring)

        # 2. a cream backing disc, just for contrast against the busy rings —
        # deliberately smaller than the beast so the beast overflows it.
        self.disc = ui.box(s, _CX - 50, _CY - 50, 100, 100, ui.CREAM, radius=50)
        self.disc.set_style_border_width(4, 0)
        self.disc.set_style_border_color(ui.hexc(ui.GOLD), 0)

        # the beast itself: big, and drawn straight onto the screen (NOT a child
        # of the disc, so it isn't clipped) so it floats ON TOP of the rings —
        # its silhouette spills past the disc onto the rainbow. It bounces.
        self.sprite = art.creature_panel(s, self.c, 8, animate=True)  # 128px
        self.sprite.align(lv.ALIGN.CENTER, 0, _CY - 120)

        # 3. flashing title + cycling praise.
        self.title = ui.label(
            s, "* LEGENDARISCH *", 0, 6, ui.GOLD, ui.font_title(), w=320, center=True
        )
        self.praise = ui.label(
            s, PRAISE[0], 0, 30, ui.CREAM, ui.font_small(), w=320, center=True
        )

        # 4. name + dossier line, just under the disc.
        ui.label(
            s, self.c["naam"], 0, 160, ui.CREAM, ui.font_title(), w=320, center=True
        )
        ui.label(
            s,
            "toegevoegd aan je boek!",
            0,
            184,
            ui.CREAM,
            ui.font_small(),
            w=320,
            center=True,
        )

        # 5. confetti — a full-screen, click-through layer of falling chips.
        self.layer = ui.box(s, 0, 0, 320, 240)
        self.cf = []  # (widget, x, y, vy, sway_phase)
        for i in range(_CONFETTI):
            w = random.randint(5, 8)
            h = random.randint(6, 11)
            piece = ui.box(self.layer, 0, 0, w, h, RAINBOW[i % len(RAINBOW)], radius=1)
            x = random.randint(0, 312)
            y = random.randint(-240, 0)
            self.cf.append([piece, x, y, random.randint(4, 9), random.uniform(0, 6.2)])
            piece.set_pos(x, y)

        # 6. sparkles around the disc — twinkle on/off out of phase.
        self.sparks = []
        for sx, sy in ((96, 52), (224, 56), (84, 150), (236, 146), (152, 28)):
            star = art.draw_sprite(self.layer, _STAR, {"w": 0xFFFFFF}, 3)
            star.set_pos(sx, sy)
            self.sparks.append(star)

    # ── lifecycle ──────────────────────────────────────────────────────────
    def start(self):
        sound.play("legendary")
        # The first chase tells us whether there are real LEDs: write() returns
        # False on desktop. Cache it so _tick doesn't redo 6 no-op calls.
        self._leds = self._led_chase(0)
        self.timer = lv.timer_create(self._tick, _TICK_MS, None)

    def stop(self):
        if self.timer:
            self.timer.delete()
            self.timer = None
        if self._leds:
            leds.off()

    def _led_chase(self, frame):
        return leds.write([_rgb(RAINBOW[(frame + i) % len(RAINBOW)]) for i in range(5)])

    # ── the dopamine pump ────────────────────────────────────────────────
    def _tick(self, t):
        f = self.frame = self.frame + 1

        # bg wash: a slow dark rainbow drift so the foreground always pops.
        if f % 3 == 0:
            self.s.set_style_bg_color(
                ui.hexc(_dim(RAINBOW[(f // 3) % len(RAINBOW)], 0.30)), 0
            )

        # halo shimmer: rotate which hue each ring wears.
        for i, ring in enumerate(self.rings):
            ring.set_style_bg_color(ui.hexc(RAINBOW[(i + f // 2) % len(RAINBOW)]), 0)

        # beast: bounce vertically + pulse the gold ring through the rainbow.
        dy = int(-6 * math.sin(f * 0.45))
        self.sprite.align(lv.ALIGN.CENTER, 0, _CY - 120 + dy)
        self.disc.set_style_border_color(ui.hexc(RAINBOW[(f // 2) % len(RAINBOW)]), 0)

        # title flashes through bright hues; praise cycles its message.
        self.title.set_style_text_color(ui.hexc(_BRIGHT[(f // 2) % len(_BRIGHT)]), 0)
        if f % 9 == 0:
            self.praise.set_text(PRAISE[(f // 9) % len(PRAISE)])

        # confetti: fall, sway, recolour, wrap back to the top.
        for c in self.cf:
            piece, x, y, vy, ph = c
            y += vy
            if y > 240:
                y = -12
                x = random.randint(0, 312)
                c[1] = x
            c[2] = y
            piece.set_pos(x + int(6 * math.sin(f * 0.2 + ph)), int(y))
            piece.set_style_bg_color(ui.hexc(RAINBOW[(f // 4 + int(ph)) % 8]), 0)

        # sparkles twinkle out of phase.
        for i, star in enumerate(self.sparks):
            if (f // 3 + i) % 2:
                star.remove_flag(lv.obj.FLAG.HIDDEN)
            else:
                star.add_flag(lv.obj.FLAG.HIDDEN)

        # rainbow chase across the 5 LEDs (badge only).
        if self._leds:
            self._led_chase(f)

        # loop the fanfare so the music never stops while the screen is up.
        if f % _FANFARE_TICKS == 0:
            sound.play("legendary")


# ── the rare shimmer ────────────────────────────────────────────────────────
_TWINKLE_MS = 120  # slower beat than the fireworks: a shimmer, not a strobe

# Around the calm card (114,36 92x92) and its name line — never on top of
# either, and clear of the VERDER button at the bottom.
_STAR_SPOTS = (
    (104, 22),
    (216, 26),
    (70, 46),
    (246, 54),
    (56, 104),
    (252, 112),
    (156, 12),
)


class Stardust:
    """The rare-catch payoff on the calm card: stars twinkling around it, the
    card border glinting gold, and the LEDs breathing gold. Same lifecycle
    contract as Fireworks (start/stop around onResume/onPause); the catch
    jingle itself still comes from the code screen, like any base catch."""

    def __init__(self, screen, panel):
        self.panel = panel
        self.timer = None
        self.frame = 0
        self._leds = False  # set in start(): True only when real NeoPixels answered
        self.stars = []
        for i, (sx, sy) in enumerate(_STAR_SPOTS):
            colour = ui.GOLD if i % 2 else 0xFFF7E6
            star = art.draw_sprite(screen, _STAR, {"w": colour}, 2)
            star.set_pos(sx, sy)
            self.stars.append(star)

    def start(self):
        self._leds = leds.write([_rgb(ui.GOLD)] * 5)
        self.timer = lv.timer_create(self._tick, _TWINKLE_MS, None)

    def stop(self):
        if self.timer:
            self.timer.delete()
            self.timer = None
        if self._leds:
            leds.off()

    def _tick(self, t):
        f = self.frame = self.frame + 1

        # stars twinkle out of phase — each spends a third of the time dark.
        for i, star in enumerate(self.stars):
            if (f // 2 + i) % 3:
                star.remove_flag(lv.obj.FLAG.HIDDEN)
            else:
                star.add_flag(lv.obj.FLAG.HIDDEN)

        # the card border glints gold now and then, then settles back.
        glint = (f // 4) % 3 == 0
        self.panel.set_style_border_color(ui.hexc(ui.GOLD if glint else ui.GREEN_D), 0)

        # LEDs breathe gold (badge only) — never fully dark, never a flash.
        if self._leds:
            lvl = 0.25 + 0.75 * (0.5 + 0.5 * math.sin(f * 0.35))
            leds.write([_rgb(_dim(ui.GOLD, lvl))] * 5)
