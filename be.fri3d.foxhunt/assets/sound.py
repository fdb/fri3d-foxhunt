# sound.py — tiny feedback layer: buzzer (RTTTL) + NeoPixels (merged leds.py).
#
# RTTTL = Nokia ringtone strings, so no audio assets are needed. On the badge a
# "buzzer" output is registered (pin 38) and these play; on desktop there is no
# buzzer output, so play() silently no-ops. One swap point to add WAV later.

from mpos import AudioManager

_TUNES = {
    "tap": "Tap:d=16,o=6,b=400:c",
    # Simon pads: one note per pad, the classic rising quad.
    "sim0": "S0:d=8,o=5,b=320:c",
    "sim1": "S1:d=8,o=5,b=320:e",
    "sim2": "S2:d=8,o=5,b=320:g",
    "sim3": "S3:d=8,o=6,b=320:c",
    "warmer": "Warm:d=16,o=6,b=320:e,g",
    "caught": "Win:d=16,o=6,b=260:c,e,g,8c7",
    "error": "Err:d=8,o=5,b=300:c,p,c",
    # Legendary fanfare: a rising triumphant flourish for the Knoricorn catch.
    # Longer + climbs to a held high note — the audio half of the dopamine hit.
    "legendary": (
        "Legend:d=16,o=5,b=200:"
        "g,g,g,8g,8e6,8c6,g,8e6,8c6,2g6,"
        "8a6,8b6,c7,8b6,8a6,8b6,2c7,8g6,8c7,4e7,2c7"
    ),
}


# The mute flag, cached — same deal as leds.brightness(). store.settings()
# builds a SharedPreferences instance, and that READS AND PARSES config.json
# every time; play() is called per dance note, per catch, per tap, inside game
# loops that tick at 50 ms. Reading the whole save file to answer "is sound
# on?" is the wrong price for a beep. Only the instellingen screen changes it,
# and it calls set_muted() (screen_settings._flip_geluid).
_muted = None


def muted():
    global _muted
    if _muted is None:
        import store

        _muted = not store.settings()["geluid"]
    return _muted


def set_muted(on):
    """Apply a new geluid setting without a restart."""
    global _muted
    _muted = bool(on)


# The output handle, cached for the same reason as _muted: play() runs inside
# 50 ms game loops, and rescanning get_outputs() with a getattr per output to
# re-answer "is there a buzzer?" costs the same every time — outputs register
# at boot and never change while the app runs. False caches "there is none"
# (desktop), so the scan happens exactly once either way.
_output = None


def _buzzer_output():
    global _output
    if _output is None:
        _output = False
        try:
            for out in AudioManager.get_outputs():
                if getattr(out, "kind", None) == "buzzer":
                    _output = out
                    break
        except Exception:
            pass
    return _output or None


# The player last started, so stop() can cut a long tune. Only the ~4.3 s
# legendary fanfare needs it; the UI beeps are over before anyone could ask.
_last = None


def play(event):
    global _last
    tune = _TUNES.get(event)
    if not tune:
        return
    if muted():  # muted from the instellingen screen
        return
    out = _buzzer_output()
    if not out:  # desktop: no buzzer -> stay silent
        return
    try:
        _last = AudioManager.rtttl_player(tune, output=out, volume=60)
        _last.start()
    except Exception as e:
        print("sound: could not play", event, e)


def stop():
    """Cut whatever is playing right now. celebrate.Fireworks.stop() calls
    this so the looping legendary fanfare dies with the screen instead of
    playing over the next one for up to 4 seconds."""
    global _last
    p, _last = _last, None
    if p:
        try:
            p.stop()
        except Exception:
            pass


# ── NeoPixels (formerly leds.py; merged for LittleFS block economy) ─────────
# Hot/cold on the 5 physical NeoPixels (mpos.lights).
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
# Everything here is ordered as you SEE it: index 0 = leftmost (coldest),
# 4 = rightmost (hottest), same as the on-screen mirror. The strip itself is
# wired the other way round — physical pixel 0 is the RIGHTMOST one — so
# write() is the single place that flips; no caller should think about it.
#
# "Unlit" means two different things: a NeoPixel must go fully dark (0,0,0),
# while the on-screen mirror needs a visible dark cell so the row of five stays
# readable. Hence OFF (physical) vs MIRROR_OFF (LCD).

import mpos.lights as lights

_LM = lights if hasattr(lights, "set_led") else lights.LightsManager

OFF = (0, 0, 0)
MIRROR_OFF = (24, 22, 18)

_scale = None  # 0.0..1.0, lazily read from the "led" setting


def brightness():
    """LED strength 0..100, from settings (cached — the hunt polls at 4 Hz)."""
    global _scale
    if _scale is None:
        import store

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
