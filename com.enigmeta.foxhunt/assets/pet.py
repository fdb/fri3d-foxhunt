# pet.py — the care rules for a caught creature. PURE: no LVGL, no mpos, no I/O.
#
# A caught creature has a state dict (see default_state). store.py persists it
# and stamps the wall-clock; this module only does the math, so it runs under
# `uv run pet.py` for a quick self-test. Living stats are ints 0..100.

# Living stats, in display order: (key, dutch label).
STATS = (
    ("bond", "binding"),
    ("energy", "energie"),
)

# Decay per hour away (applied on each visit). binding never decays — loyalty.
_DECAY = {"energy": -4}


def _clamp(v):
    return 0 if v < 0 else 100 if v > 100 else v


def default_state(date, place, now):
    """Fresh pet state, the moment the creature is caught."""
    return {
        "date": date,  # gevonden op (YYYY-MM-DD)
        "place": place,  # plaats
        "sightings": 1,  # waarnemingen
        "bijnaam": "",  # nickname (falls back to the creature name)
        "bond": 10,
        "energy": 75,
        "last": now,  # epoch seconds of last update
    }


# ── presentation helpers (derive the screens' segments / hearts / level) ────
# 25 bond points per level, so level 5 == bond 100 == finished. Bond comes
# from play (+6, favourite game +10) with a token from feeding (+1/+2), so
# the road from 10 to 100 is a solid day of care — never one pat.
LEVEL_MAX = 5


def segments(value, total=5):
    """A 0..100 stat as a lit-segment count 0..total (round to nearest cell)."""
    return min(total, max(0, int(value * total / 100 + 0.5)))


def energy_segments(value):
    """Complete spendable energy segments; one cell pays for one-cost play."""
    return min(5, max(0, int(value) // SEG))


def level(bond):
    """1..5, every 25 bond points is a level; 5 only at max bond."""
    return min(LEVEL_MAX, 1 + bond // 25)


def hearts(bond):
    """Filled Band hearts (== level) out of 5."""
    return level(bond)


def level_pct(bond):
    """Percent toward the next level (100 once maxed)."""
    if level(bond) >= LEVEL_MAX:
        return 100
    return (bond % 25) * 4


def finished(state):
    """Beste vriend: bond maxed. The creature retires from the economy —
    stats frozen, play free forever — but not from the game."""
    return state.get("bond", 0) >= 100


def _finish(s):
    """The moment bond reaches 100: permanently content. Snap energy to
    rest so no screen ever shows a tired beste vriend."""
    if s["bond"] >= 100:
        s["energy"] = 100
    return s


def decay(state, now):
    """Age the living stats by the real time elapsed since state['last'].
    Returns a new dict; clamps to 0..100 so long absences can't overflow.
    A finished friend does not age — permanently content.

    Decay applies in WHOLE hours and `last` advances only by the hours
    consumed, never to `now`: stamping `now` while int() truncated the
    sub-hour part to zero threw the remainder away on every visit, so a
    player hopping between the beest page, the school and the feed screen
    every few minutes never accumulated any decay at all — the per-hour
    economy silently did not apply during active play."""
    s = dict(state)
    # Migration: saves from before energy replaced hunger still carry the
    # key. Every store path runs decay and persists the result, so popping
    # it here retires it from old badges on their first touch.
    s.pop("hunger", None)
    if finished(s):
        s["last"] = now
        return _finish(s)
    base = s.get("last", now)
    hours = int(max(0, now - base) // 3600)
    if hours > 0:
        for key, rate in _DECAY.items():
            s[key] = _clamp(s.get(key, 0) + rate * hours)
        s["last"] = base + hours * 3600
    return s


def feed(state, food, favoriet, now):
    """Feed a specific hapje. Returns (new_state, ok, message, is_favourite).
    Food IS the energy refill — eating is how a tired creature gets to play
    again; the favourite grants extra ENERGY ('favoriet = meer energie');
    bond stays token — band komt van spelen. Refuse above 80 so a plain
    hapje (+20) always fits whole: the pantry is never wasted on a
    creature that is already full."""
    s = dict(state)
    if finished(s):
        s["last"] = now
        return s, False, "hoeft niet meer te eten", False
    if s.get("energy", 0) > 80:
        s["last"] = now
        return s, False, "zit vol energie!", False
    is_fav = food == favoriet
    s["energy"] = _clamp(s.get("energy", 0) + (35 if is_fav else 20))
    s["bond"] = _clamp(s.get("bond", 0) + (2 if is_fav else 1))
    s["last"] = now
    return _finish(s), True, ("favoriet! extra energie" if is_fav else "mmm!"), is_fav


# One energy segment (the 5-cell meter) in 0..100 stat points.
SEG = 20


def play(state, cost, favourite, now):
    """A beestenschool session: spend `cost` energy segments, earn bond.
    Returns (new_state, ok, message). The playful refusal when energy is
    short IS the rate limit on bond — never a punishment, just 'eerst een
    hapje'. A favourite game earns extra bond. A finished friend plays free,
    forever, and earns nothing — warmth only, or free play becomes the
    infinite farming route."""
    s = dict(state)
    if finished(s):
        s["last"] = now
        return _finish(s), True, "wat een lol!"
    if s.get("energy", 0) < cost * SEG:
        s["last"] = now
        return s, False, "te moe om te spelen"
    s["energy"] = _clamp(s.get("energy", 0) - cost * SEG)
    s["bond"] = _clamp(s.get("bond", 0) + (10 if favourite else 6))
    s["last"] = now
    return (
        _finish(s),
        True,
        ("favoriet spel! ++band" if favourite else "wat een lol! +band"),
    )


if __name__ == "__main__":
    # Quick self-test: catch -> age a day -> feed/pet/play -> refusals.
    st = default_state("2026-06-06", "Fri3d Camp", 1000)
    assert st["energy"] == 75 and st["sightings"] == 1
    assert "hunger" not in st
    aged = decay(st, 1000 + 24 * 3600)  # +24h
    assert aged["energy"] == 0, aged  # 75 - 4*24, clamped
    # presentation helpers: 25-point levels, 5 only at max
    assert segments(0) == 0 and segments(100) == 5 and segments(50) == 3, segments(50)
    assert energy_segments(19) == 0 and energy_segments(20) == 1
    assert energy_segments(39) == 1 and energy_segments(40) == 2
    assert level(0) == 1 and level(50) == 3 and level(99) == 4, level(99)
    assert level(100) == 5 and hearts(100) == 5
    assert level_pct(30) == 20 and level_pct(100) == 100, level_pct(30)
    # favourite food grants more ENERGY than a plain hapje (band comes from play)
    base = dict(st)
    base["energy"] = 40
    plain, ok, _, fav = feed(base, "noot", "bes", st["last"])
    assert ok and not fav and plain["energy"] == 60, plain
    assert plain["bond"] == base["bond"] + 1, plain
    favd, ok, _, fav = feed(base, "bes", "bes", st["last"])
    assert ok and fav and favd["energy"] == 75, favd
    # full: above 80 a hapje would overflow — refuse instead of wasting it
    full = dict(st)
    full["energy"] = 81
    _, ok, msg, _ = feed(full, "bes", "bes", st["last"])
    assert not ok and msg == "zit vol energie!", (ok, msg)
    edge = dict(st)
    edge["energy"] = 80
    fed, ok, _, _ = feed(edge, "noot", "bes", st["last"])
    assert ok and fed["energy"] == 100, fed
    # eat -> play: the refill IS what pays for the session (no second gate)
    tired = dict(st)
    tired["energy"] = 0
    _, ok, msg = play(tired, 1, False, st["last"])
    assert not ok and msg == "te moe om te spelen", (ok, msg)
    fed, ok, _, _ = feed(tired, "noot", "bes", st["last"])
    played, ok, _ = play(fed, 1, False, st["last"])
    assert ok and played["energy"] == 0, played
    # a beestenschool session: costs energy segments, earns real bond
    played, ok, msg = play(base, 2, False, st["last"])
    assert ok and played["energy"] == 0 and played["bond"] == base["bond"] + 6, played
    played, ok, msg = play(base, 2, True, st["last"])
    assert ok and played["bond"] == base["bond"] + 10, played
    low = dict(base)
    low["energy"] = 19
    _, ok, msg = play(low, 1, False, st["last"])
    assert not ok and msg == "te moe om te spelen", (ok, msg)
    # the finish: crossing 100 snaps to permanently content...
    near = dict(st)
    near["bond"] = 95
    near["energy"] = 40
    done, ok, _ = play(near, 1, True, st["last"])
    assert ok and done["bond"] == 100 and finished(done), done
    assert done["energy"] == 100, done
    # ...then never decays, never eats, and plays free forever
    later = decay(done, st["last"] + 48 * 3600)
    assert later["energy"] == 100, later
    _, ok, msg, _ = feed(done, "bes", "bes", st["last"])
    assert not ok and msg == "hoeft niet meer te eten", (ok, msg)
    freeplay, ok, msg = play(done, 2, True, st["last"])
    assert ok and msg == "wat een lol!", (ok, msg)
    assert freeplay["energy"] == 100 and freeplay["bond"] == 100, freeplay
    # Legacy max-bond saves are normalized too, even if they were persisted
    # before the permanent-content rule started snapping their living stats.
    legacy_done = dict(done)
    legacy_done["energy"] = 0
    normalized = decay(legacy_done, st["last"] + 3600)
    assert normalized["energy"] == 100, normalized
    # Migration: a save from the hunger era loses the key on its first
    # decay pass; the stored energy value is kept as-is.
    legacy = dict(st)
    legacy["hunger"] = 90
    legacy["energy"] = 10
    migrated = decay(legacy, st["last"] + 3600)
    assert "hunger" not in migrated, migrated
    assert migrated["energy"] == 6, migrated  # 10 - 4*1h, nothing converted
    print("pet.py self-test OK")
