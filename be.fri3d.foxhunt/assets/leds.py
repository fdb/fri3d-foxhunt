# leds.py — hot/cold on the 5 physical NeoPixels (mpos.lights).
#
# On the badge: drives the 5 GPIO12 NeoPixels.
# On desktop:   no NeoPixel -> set_led()/write() are no-ops that return False,
#               and the hunt screen's on-screen 5-LED mirror uses
#               colors_for_level() instead.
# We deliberately only use set_led() + write() (never is_available()/clear()):
# those two are the oldest, most stable part of the mpos.lights API, so the app
# runs on badge firmware older than this checkout's mpos.
# index 0 = leftmost (coldest), 4 = rightmost (hottest) — matches the board.

import mpos.lights as lights

OFF = (24, 22, 18)


def _seg_color(i):
    if i >= 4:
        return (0xCF, 0x6A, 0x3F)  # terra  (hot)
    if i >= 2:
        return (0xE8, 0xB2, 0x3A)  # gold
    return (0x5A, 0x9A, 0x3C)  # green  (cold)


def colors_for_level(level):
    """RGB tuple per LED for a given lit count (0..5). Used by both the
    physical LEDs and the on-screen mirror so they always agree."""
    return [_seg_color(i) if i < level else OFF for i in range(5)]


def show_level(level):
    """Light the physical NeoPixels. Returns False (no-op) on desktop."""
    for i, (r, g, b) in enumerate(colors_for_level(level)):
        lights.set_led(i, r, g, b)
    return lights.write()


def off():
    """Blank the physical NeoPixels. Returns False (no-op) on desktop."""
    for i in range(5):
        lights.set_led(i, 0, 0, 0)
    return lights.write()
