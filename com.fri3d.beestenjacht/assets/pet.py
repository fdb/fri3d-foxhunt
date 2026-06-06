# pet.py — the living-companion rules. PURE: no LVGL, no mpos, no I/O.
#
# A caught creature has a state dict (see default_state). store.py persists it
# and stamps the wall-clock; this module only does the math, so it runs under
# `uv run pet.py` for a quick self-test. Living stats are ints 0..100.

# Living stats, in display order: (key, dutch label).
STATS = (
    ("bond",   "binding"),
    ("mood",   "humeur"),
    ("energy", "energie"),
    ("hunger", "honger"),
)

# Decay per hour away (applied on each visit). binding never decays — loyalty.
_DECAY = {"hunger": +6, "energy": -4, "mood": -3}

# Action effects: deltas applied when the creature accepts.
_ACTIONS = {
    "voeden": {"hunger": -35, "energy": +8, "bond": +3, "mood": +4},
    "aaien":  {"mood": +12, "bond": +5, "energy": +2},
    "spelen": {"mood": +18, "bond": +8, "energy": -18, "hunger": +12},
}


def _clamp(v):
    return 0 if v < 0 else 100 if v > 100 else v


def default_state(date, place, now):
    """Fresh companion, the moment it's caught."""
    return {
        "date": date,           # gevonden op (YYYY-MM-DD)
        "place": place,         # plaats
        "sightings": 1,         # waarnemingen
        "bond": 10,
        "mood": 65,
        "energy": 75,
        "hunger": 25,
        "last": now,            # epoch seconds of last update
    }


def decay(state, now):
    """Age the living stats by the real time elapsed since state['last'].
    Returns a new dict; clamps to 0..100 so long absences can't overflow."""
    s = dict(state)
    hours = max(0, (now - s.get("last", now))) / 3600
    if hours > 0:
        for key, rate in _DECAY.items():
            s[key] = _clamp(s.get(key, 0) + int(rate * hours))
        s["last"] = now
    return s


def act(state, action, now):
    """Apply an action. Returns (new_state, ok, message).

    Some actions are refused for personality — a full creature won't eat, a
    tired one won't play — so stats actually constrain what you can do."""
    s = dict(state)
    if action == "voeden" and s.get("hunger", 0) <= 8:
        s["mood"] = _clamp(s.get("mood", 0) - 2)
        s["last"] = now
        return s, False, "zit vol!"
    if action == "spelen" and s.get("energy", 0) < 20:
        s["mood"] = _clamp(s.get("mood", 0) - 1)
        s["last"] = now
        return s, False, "te moe om te spelen"

    deltas = _ACTIONS.get(action)
    if not deltas:
        return s, False, ""
    for key, d in deltas.items():
        s[key] = _clamp(s.get(key, 0) + d)
    s["last"] = now
    return s, True, _OK_MSG[action]


_OK_MSG = {"voeden": "smikkelt!", "aaien": "spint van plezier", "spelen": "wat een lol!"}


def face(state):
    """Derive an ASCII mood face + word from the stats (font is ASCII-only).
    Order matters: urgent needs (honger, moe) win over general mood."""
    if state.get("hunger", 0) >= 75:
        return ">_<", "honger!"
    if state.get("energy", 0) <= 20:
        return "-_-", "moe"
    if state.get("mood", 0) >= 70:
        return "^_^", "blij"
    if state.get("mood", 0) <= 30:
        return "T_T", "sip"
    return "o_o", "oke"


if __name__ == "__main__":
    # Quick self-test: catch -> age a day -> feed/pet/play -> refusals.
    st = default_state("2026-06-06", "Fri3d Camp", 1000)
    assert st["hunger"] == 25 and st["sightings"] == 1
    aged = decay(st, 1000 + 24 * 3600)          # +24h
    assert aged["hunger"] == 100, aged          # 25 + 6*24, clamped
    assert aged["energy"] == 0, aged            # 75 - 4*24, clamped
    fed, ok, msg = act(aged, "voeden", aged["last"])
    assert ok and fed["hunger"] == 65, (fed, msg)
    tired, ok, msg = act(aged, "spelen", aged["last"])
    assert not ok and msg == "te moe om te spelen", (ok, msg)
    full = dict(st); full["hunger"] = 5
    _, ok, msg = act(full, "voeden", st["last"])
    assert not ok and msg == "zit vol!", (ok, msg)
    assert face({"hunger": 80})[1] == "honger!"
    assert face({"hunger": 10, "energy": 10})[1] == "moe"
    assert face({"hunger": 10, "energy": 90, "mood": 80})[1] == "blij"
    print("pet.py self-test OK")
