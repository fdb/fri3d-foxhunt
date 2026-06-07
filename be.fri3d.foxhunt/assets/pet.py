# pet.py — the living-companion rules. PURE: no LVGL, no mpos, no I/O.
#
# A caught creature has a state dict (see default_state). store.py persists it
# and stamps the wall-clock; this module only does the math, so it runs under
# `uv run pet.py` for a quick self-test. Living stats are ints 0..100.

# Living stats, in display order: (key, dutch label).
STATS = (
    ("bond", "binding"),
    ("mood", "humeur"),
    ("energy", "energie"),
    ("hunger", "honger"),
)

# Decay per hour away (applied on each visit). binding never decays — loyalty.
_DECAY = {"hunger": +6, "energy": -4, "mood": -3}

# Action effects: deltas applied when the creature accepts.
_ACTIONS = {
    "voeden": {"hunger": -35, "energy": +8, "bond": +3, "mood": +4},
    "aaien": {"mood": +12, "bond": +5, "energy": +2},
    "spelen": {"mood": +18, "bond": +8, "energy": -18, "hunger": +12},
}


def _clamp(v):
    return 0 if v < 0 else 100 if v > 100 else v


def default_state(date, place, now):
    """Fresh companion, the moment it's caught."""
    return {
        "date": date,  # gevonden op (YYYY-MM-DD)
        "place": place,  # plaats
        "sightings": 1,  # waarnemingen
        "bijnaam": "",  # nickname (falls back to the creature name)
        "bond": 10,
        "mood": 65,
        "energy": 75,
        "hunger": 25,
        "last": now,  # epoch seconds of last update
    }


# ── presentation helpers (derive the screens' segments / hearts / level) ────
LEVEL_MAX = 5


def segments(value, total=5):
    """A 0..100 stat as a lit-segment count 0..total (round to nearest cell)."""
    return min(total, max(0, int(value * total / 100 + 0.5)))


def level(bond):
    """1..5, every 20 bond points is a level."""
    return min(LEVEL_MAX, 1 + bond // 20)


def hearts(bond):
    """Filled Band hearts (== level) out of 5."""
    return level(bond)


def level_pct(bond):
    """Percent toward the next level (100 once maxed)."""
    if level(bond) >= LEVEL_MAX:
        return 100
    return (bond % 20) * 5


def fullness(hunger):
    """VERZADIGD meter: how full the creature is (inverse of hunger)."""
    return 100 - hunger


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


_OK_MSG = {
    "voeden": "smikkelt!",
    "aaien": "spint van plezier",
    "spelen": "wat een lol!",
}


def feed(state, food, favoriet, now):
    """Feed a specific hapje. Returns (new_state, ok, message, is_favourite).
    The creature's favourite food grants extra band ('favoriet = +1 band')."""
    s = dict(state)
    if s.get("hunger", 0) <= 8:
        s["mood"] = _clamp(s.get("mood", 0) - 2)
        s["last"] = now
        return s, False, "zit vol!", False
    is_fav = food == favoriet
    s["hunger"] = _clamp(s.get("hunger", 0) - 35)
    s["energy"] = _clamp(s.get("energy", 0) + 8)
    s["mood"] = _clamp(s.get("mood", 0) + (8 if is_fav else 4))
    s["bond"] = _clamp(s.get("bond", 0) + (8 if is_fav else 3))
    s["last"] = now
    return s, True, ("favoriet! +band" if is_fav else "mmm!"), is_fav


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
    aged = decay(st, 1000 + 24 * 3600)  # +24h
    assert aged["hunger"] == 100, aged  # 25 + 6*24, clamped
    assert aged["energy"] == 0, aged  # 75 - 4*24, clamped
    fed, ok, msg = act(aged, "voeden", aged["last"])
    assert ok and fed["hunger"] == 65, (fed, msg)
    tired, ok, msg = act(aged, "spelen", aged["last"])
    assert not ok and msg == "te moe om te spelen", (ok, msg)
    full = dict(st)
    full["hunger"] = 5
    _, ok, msg = act(full, "voeden", st["last"])
    assert not ok and msg == "zit vol!", (ok, msg)
    assert face({"hunger": 80})[1] == "honger!"
    assert face({"hunger": 10, "energy": 10})[1] == "moe"
    assert face({"hunger": 10, "energy": 90, "mood": 80})[1] == "blij"
    # presentation helpers
    assert segments(0) == 0 and segments(100) == 5 and segments(50) == 3, segments(50)
    assert level(0) == 1 and level(50) == 3 and level(100) == 5, level(50)
    assert hearts(50) == 3
    assert level_pct(50) == 50 and level_pct(100) == 100, level_pct(50)
    assert fullness(25) == 75
    # favourite food grants more band than a plain hapje
    base = dict(st)
    base["hunger"] = 60
    plain, ok, _, fav = feed(base, "noot", "bes", st["last"])
    assert ok and not fav and plain["bond"] == base["bond"] + 3, plain
    favd, ok, _, fav = feed(base, "bes", "bes", st["last"])
    assert ok and fav and favd["bond"] == base["bond"] + 8, favd
    print("pet.py self-test OK")
