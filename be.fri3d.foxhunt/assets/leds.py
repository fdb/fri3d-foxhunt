# leds.py — hot/cold on the 5 physical NeoPixels (mpos.lights).
#
# On the badge: drives the 5 GPIO12 NeoPixels.
# On desktop:   no NeoPixel -> set_led()/write() are no-ops that return False,
#               and the hunt screen's on-screen 5-LED mirror uses
#               colors_for_level() instead.
# We deliberately only use set_led() + write() (never is_available()/clear()):
# those two are the oldest, most stable part of the mpos.lights API, so the app
# runs on badge firmware older than this checkout's mpos. They started as
# module-level functions and moved onto a LightsManager singleton; _LM picks
# whichever this firmware has.
# Everything in this module is ordered as you SEE it: index 0 = leftmost
# (coldest), 4 = rightmost (hottest), same as the on-screen mirror. The strip
# itself is wired the other way round — physical pixel 0 is the RIGHTMOST one —
# so write() is the single place that flips; no caller should think about it.
#
# "Unlit" means two different things: a NeoPixel must go fully dark (0,0,0),
# while the on-screen mirror needs a visible dark cell so the row of five stays
# readable. Hence OFF (physical) vs MIRROR_OFF (LCD).

import mpos.lights as lights
import store

_LM = lights if hasattr(lights, "set_led") else lights.LightsManager

OFF = (0, 0, 0)
MIRROR_OFF = (24, 22, 18)

_scale = None  # 0.0..1.0, lazily read from the "led" setting


def brightness():
    """LED strength 0..100, from settings (cached — the hunt polls at 4 Hz)."""
    global _scale
    if _scale is None:
        _scale = max(0, min(100, store.settings()["led"])) / 100.0
    return _scale


def set_brightness(pct):
    """Apply a new strength without a restart (called by the settings screen)."""
    global _scale
    _scale = max(0, min(100, pct)) / 100.0


def dim(rgb):
    """Scale an RGB tuple by the configured strength, for physical LEDs only —
    the on-screen mirror shows full colour so it stays legible on the LCD."""
    b = brightness()
    return (int(rgb[0] * b), int(rgb[1] * b), int(rgb[2] * b))


def _seg_color(i):
    if i >= 4:
        return (0xCF, 0x6A, 0x3F)  # terra  (hot)
    if i >= 2:
        return (0xE8, 0xB2, 0x3A)  # gold
    return (0x5A, 0x9A, 0x3C)  # green  (cold)


def colors_for_level(level, off=MIRROR_OFF):
    """RGB tuple per LED for a given lit count (0..5). Used by both the
    physical LEDs and the on-screen mirror so they always agree on which
    segments are lit; they differ only in what "unlit" looks like."""
    return [_seg_color(i) if i < level else off for i in range(5)]


def write(colors):
    """Push 5 left-to-right RGB tuples to the strip, dimmed to the configured
    strength and flipped to the board's right-to-left pixel order.
    Returns False (no-op) on desktop."""
    last = len(colors) - 1
    for i, rgb in enumerate(colors):
        r, g, b = dim(rgb)
        _LM.set_led(last - i, r, g, b)
    return _LM.write()


def show_level(level):
    """Light the physical NeoPixels. Returns False (no-op) on desktop."""
    return write(colors_for_level(level, OFF))


def off():
    """Blank the physical NeoPixels. Returns False (no-op) on desktop."""
    for i in range(5):
        _LM.set_led(i, 0, 0, 0)
    return _LM.write()
