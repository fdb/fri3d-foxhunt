# leds.py — hot/cold on the 5 physical NeoPixels (mpos.lights).
#
# On the badge: lights.is_available() is True -> drives GPIO12 NeoPixels.
# On desktop:   not available -> show_level() is a no-op; the hunt screen's
#               on-screen 5-LED mirror uses colors_for_level() instead.
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
    if not lights.is_available():
        return False
    for i, (r, g, b) in enumerate(colors_for_level(level)):
        lights.set_led(i, r, g, b)
    return lights.write()


def off():
    if lights.is_available():
        lights.clear()
        lights.write()
