# sound.py — tiny UI sound layer over mpos.AudioManager (buzzer / RTTTL).
#
# RTTTL = Nokia ringtone strings, so no audio assets are needed. On the badge a
# "buzzer" output is registered (pin 38) and these play; on desktop there is no
# buzzer output, so play() silently no-ops. One swap point to add WAV later.

from mpos import AudioManager

_TUNES = {
    "tap": "Tap:d=16,o=6,b=400:c",
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
    import store

    if not store.settings()["geluid"]:  # muted from the instellingen screen
        return
    out = _buzzer_output()
    if not out:  # desktop: no buzzer -> stay silent
        return
    try:
        AudioManager.rtttl_player(tune, output=out, volume=60).start()
    except Exception as e:
        print("sound: could not play", event, e)
