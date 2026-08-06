# sound.py — tiny UI sound layer over mpos.AudioManager (buzzer / RTTTL).
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


def _buzzer_output():
    try:
        for out in AudioManager.get_outputs():
            if getattr(out, "kind", None) == "buzzer":
                return out
    except Exception:
        pass
    return None


def play(event):
    tune = _TUNES.get(event)
    if not tune:
        return
    if muted():  # muted from the instellingen screen
        return
    out = _buzzer_output()
    if not out:  # desktop: no buzzer -> stay silent
        return
    try:
        AudioManager.rtttl_player(tune, output=out, volume=60).start()
    except Exception as e:
        print("sound: could not play", event, e)
