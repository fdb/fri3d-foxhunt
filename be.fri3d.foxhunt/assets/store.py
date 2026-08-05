# store.py — persistent state via MicroPythonOS SharedPreferences.
# Stored at data/be.fri3d.foxhunt/config.json on both desktop and badge.
#
#   "caught"   : list of caught creature ids
#   "beast"    : dict {str(id): pet-state} — care stats per caught creature
#   "origins"  : dict {str(id): "vangst"|"spoor"|"start"} — how a creature
#                arrived (own find / vonk-geluk / startbeest); feeds the
#                dossier lineage
#   "voorraad" : dict {food: count} — the finite pantry
#   "vrienden" : list of {mac, naam, code, dag} — the vriendenboekje
#   "vonk"     : snuffel log — {date, count (daily reset), pairs: {mac:
#                {vonk: epoch, food: epoch}}} — pair cooldown timestamps
#   "pluk"     : {spots: {bssid: epoch}, date, count} — reloads + day stat
#
# pet.py owns the rules (pure); this module owns persistence + the wall-clock.

import random

from mpos import SharedPreferences
import mpos.time
import pet
from creatures import by_id

_APP = "be.fri3d.foxhunt"
_PLACE = "Fri3d Camp"  # stub: no GPS yet — see fox_radio for the backend seam


def _now():
    return mpos.time.epoch_seconds()


def _today():
    lt = mpos.time.localtime()
    return "%04d-%02d-%02d" % (lt[0], lt[1], lt[2])


def today():
    """The wall-clock day, for callers that key daily rules on it (the
    plukplek yield formula, the vonk log)."""
    return _today()


def profile():
    """The hunter profile dict, or None before registration.
    Keys: name, head, accs, bg, badge_id, hunter_id (None until minted),
    synced (True once the cloud server confirmed the save)."""
    p = SharedPreferences(_APP).get_dict("profile", None)
    return p if p else None


def save_profile(p):
    p.setdefault("since", _now())  # registration day, for the DAGEN stat
    SharedPreferences(_APP).edit().put_dict("profile", p).commit()


def update_profile(**kv):
    """Merge fields into the stored profile (e.g. the minted hunter_id)."""
    prefs = SharedPreferences(_APP)
    p = prefs.get_dict("profile", {})
    p.update(kv)
    prefs.edit().put_dict("profile", p).commit()
    return p


# What survives ALLES WISSEN. Everything at the top of this file is the player;
# these two are the badge — how loud it is and how bright it is have nothing to
# do with whose badge it is, and re-deafening yourself after a wipe is not part
# of starting over.
_KEEP_ON_RESET = ("settings",)


def reset_all():
    """Erase every trace of the player from this badge (screen_wipe).

    An ALLOWLIST, and deliberately so: Editor has no remove(key), only
    remove_all(), so the natural shape here is "wipe, then write back what
    stays". That is also the safe default — a store key added next month is
    wiped by a reset nobody remembered to update, instead of quietly surviving
    it and haunting the next player.

    One commit, so a reset cannot half-happen. When nothing is kept,
    save_config removes the file (and the app's prefs dir) outright.
    """
    prefs = SharedPreferences(_APP)
    keep = {k: prefs.get_dict(k, {}) for k in _KEEP_ON_RESET}
    e = prefs.edit().remove_all()
    for k, v in keep.items():
        if v:
            e.put_dict(k, v)
    e.commit()


# App settings (the instellingen screen).
# led is the NeoPixel duty in percent; full brightness is blinding on the
# badge, so the default sits low. The settings screen steps it on a roughly
# doubling ladder (see _LED_STEPS) because the eye is power-law, not linear.
_DEFAULT_SETTINGS = {
    "geluid": True,
    "led": 30,
    "pluk_any": False,
    "nooit_moe": False,
}


def settings():
    s = dict(_DEFAULT_SETTINGS)
    s.update(SharedPreferences(_APP).get_dict("settings", {}))
    return s


def set_setting(key, value):
    prefs = SharedPreferences(_APP)
    s = prefs.get_dict("settings", {})
    s[key] = value
    prefs.edit().put_dict("settings", s).commit()


def flag(name):
    """One-way markers: things that have happened once on this badge."""
    return name in SharedPreferences(_APP).get_list("flags", [])


def set_flag(name):
    prefs = SharedPreferences(_APP)
    f = prefs.get_list("flags", [])
    if name not in f:
        f.append(name)
        prefs.edit().put_list("flags", f).commit()


def caught_ids():
    return SharedPreferences(_APP).get_list("caught", [])


def is_caught(cid):
    return cid in caught_ids()


def add_caught(cid, origin="vangst"):
    """Add a creature. origin records HOW it arrived: "vangst" (found it
    yourself — hunt, code), "spoor" (a vonk-geluk introduction) or "start"
    (the startbeest granted at registration). Pure lineage data for the
    dossier; it gates nothing."""
    prefs = SharedPreferences(_APP)
    ids = prefs.get_list("caught", [])
    e = prefs.edit()
    if cid not in ids:
        ids.append(cid)
        e.put_list("caught", ids)
        # put_dict_item silently drops non-dict values (mpos config.py), so
        # the origin string must go through a whole-dict write.
        origins = prefs.get_dict("origins", {})
        origins[str(cid)] = origin
        e.put_dict("origins", origins)
    # First catch seeds the pet state; a recatch never overwrites its stats.
    beast = prefs.get_dict("beast", {})
    if str(cid) not in beast:
        e.put_dict_item("beast", str(cid), pet.default_state(_today(), _PLACE, _now()))
    e.commit()


def restore_caught(ids):
    """Adopt the catch list the server handed back (screen_restore).

    A union, never a replace: the server only hears about a catch when the
    LoRa bridge relays it, so a catch this badge has and the server doesn't is
    real and must survive the restore. Ids the roster doesn't know are dropped
    rather than counted — a phantom catch would inflate the maatje's unlocks.

    Pet state is seeded fresh for everything recovered: the server records
    which creatures you found, never how well you looked after them.

    Returns the caught list afterwards."""
    prefs = SharedPreferences(_APP)
    have = prefs.get_list("caught", [])
    beast = prefs.get_dict("beast", {})
    e = prefs.edit()
    changed = False
    for cid in ids:
        if by_id(cid) is None:
            continue
        if cid not in have:
            have.append(cid)
            changed = True
        if str(cid) not in beast:
            e.put_dict_item(
                "beast", str(cid), pet.default_state(_today(), _PLACE, _now())
            )
    if changed:
        e.put_list("caught", have)
    e.commit()
    return have


def remove_caught(cid):
    """Forget a catch and its pet state (debug/test support)."""
    prefs = SharedPreferences(_APP)
    ids = prefs.get_list("caught", [])
    e = prefs.edit()
    if cid in ids:
        ids.remove(cid)
        e.put_list("caught", ids)
    e.remove_dict_item("beast", str(cid))
    e.commit()


def _raw_state(prefs, cid):
    """The stored pet-state dict for cid, seeding a default for caught-but-
    unseeded creatures (legacy saves from before pet state existed). Returns
    None only if the creature isn't caught at all."""
    raw = prefs.get_dict("beast", {}).get(str(cid))
    if raw is None and cid in prefs.get_list("caught", []):
        raw = pet.default_state(_today(), _PLACE, _now())
        prefs.edit().put_dict_item("beast", str(cid), raw).commit()
    return raw


def finished_ids():
    """Ids of beste vrienden (bond maxed). Raw read, no decay pass: bond
    never decays, so the stored value is already the truth — and the home
    grid asks per tile, where a decay-persist would cost a flash write each."""
    beasts = SharedPreferences(_APP).get_dict("beast", {})
    return {int(k) for k, v in beasts.items() if pet.finished(v)}


def beast_state(cid):
    """Pet stats with time-decay applied and persisted. None if uncaught."""
    prefs = SharedPreferences(_APP)
    raw = _raw_state(prefs, cid)
    if raw is None:
        return None
    state = pet.decay(raw, _now())
    prefs.edit().put_dict_item("beast", str(cid), state).commit()
    return state


def do_action(cid, action):
    """Apply a pet action; persist; return (state, ok, message)."""
    prefs = SharedPreferences(_APP)
    raw = _raw_state(prefs, cid)
    if raw is None:
        return None, False, ""
    state, ok, msg = pet.act(pet.decay(raw, _now()), action, _now())
    prefs.edit().put_dict_item("beast", str(cid), state).commit()
    return state, ok, msg


def do_feed(cid, food):
    """Feed a hapje ('bes'|'noot'|'eikel') FROM THE VOORRAAD; persist;
    (state, ok, msg, is_fav). An empty pantry refuses before the creature
    gets a say — the hapje is only consumed when it is actually eaten.

    ONE instance, ONE editor, deliberately: SharedPreferences snapshots the
    file per instance and commit() writes the whole snapshot back, so a
    take_food() on a second instance here was silently reverted by the
    beast-state commit from the first — the pantry never drained. The
    voorraad decrement must ride the same commit as the beast state."""
    v = voorraad()  # may seed the starter pantry — must run BEFORE prefs snapshots
    prefs = SharedPreferences(_APP)
    raw = _raw_state(prefs, cid)
    if raw is None:
        return None, False, "", False
    if v.get(food, 0) <= 0:
        return pet.decay(raw, _now()), False, "op - ga plukken!", False
    c = by_id(cid)
    favoriet = c.get("favoriet") if c else None
    state, ok, msg, is_fav = pet.feed(pet.decay(raw, _now()), food, favoriet, _now())
    e = prefs.edit()
    if ok:
        v[food] -= 1
        e.put_dict("voorraad", v)
    e.put_dict_item("beast", str(cid), state).commit()
    return state, ok, msg, is_fav


def play_cost(cost):
    """What a beestenschool session really costs in energy segments — the
    tile's price normally, zero while the debug ONVERMOEIBAAR switch is on.

    Three places gate on energy (the school's tiles, the game's NOG EEN KEER,
    do_play itself) and they all ask here, so the switch can never leave one
    of them refusing while another lets you in. It suspends the *price*, not
    the reward: a free session still earns its normal band, and
    like every debug path it never leaves the badge."""
    return 0 if settings().get("nooit_moe") else cost


def do_play(cid, cost, favourite):
    """A beestenschool session; persist; return (state, ok, msg)."""
    prefs = SharedPreferences(_APP)
    raw = _raw_state(prefs, cid)
    if raw is None:
        return None, False, ""
    state, ok, msg = pet.play(
        pet.decay(raw, _now()), play_cost(cost), favourite, _now()
    )
    prefs.edit().put_dict_item("beast", str(cid), state).commit()
    return state, ok, msg


# ── voorraad: the finite pantry ─────────────────────────────────────────────
# Foraging fills it, feeding drains it. New players get a small starter so
# the first feed never hits an empty pantry (GAME_DESIGN.md: basic affection
# must never be locked out; the tutorial hands over these).
FOODS = ("bes", "noot", "eikel")
_STARTER = {"bes": 2, "noot": 1, "eikel": 1}


def voorraad():
    prefs = SharedPreferences(_APP)
    # get_dict hands back {} for a missing key, so truthiness is the "never
    # seeded" test. A legitimately empty pantry keeps its zero-count keys
    # and stays empty — only a fresh save gets the starter.
    v = prefs.get_dict("voorraad", {})
    if not v:
        v = dict(_STARTER)
        prefs.edit().put_dict("voorraad", v).commit()
    return {f: int(v.get(f, 0)) for f in FOODS}


def voorraad_total():
    return sum(voorraad().values())


def add_food(food, n=1):
    v = voorraad()
    v[food] = v.get(food, 0) + n
    SharedPreferences(_APP).edit().put_dict("voorraad", v).commit()
    return v


def take_food(food):
    """Consume one hapje. False (and no change) if the jar is empty."""
    v = voorraad()
    if v.get(food, 0) <= 0:
        return False
    v[food] -= 1
    SharedPreferences(_APP).edit().put_dict("voorraad", v).commit()
    return True


# ── snuffelen: vrienden (permanent) + vonken (cooldown-gated) ───────────────
# The vriendenboekje never decays. The vonk log holds per-pair timestamps:
# a pair scores a new vonk after ~4h (daily cap on top), and shares picknick
# food after ~1h — inside the hour a repeat snuffel pays NOTHING, so two
# badges cannot be farmed for food. Identity is the peer's MAC (snuffel_link)
# or a manual code — either way one string.
VONK_DAY_CAP = 10  # scored vonken per day: meet SOME new people, not everyone
SNF_VONK_COOLDOWN_S = 4 * 60 * 60
SNF_FOOD_COOLDOWN_S = 60 * 60


def vrienden():
    return SharedPreferences(_APP).get_list("vrienden", [])


def _vonk_log():
    d = SharedPreferences(_APP).get_dict("vonk", {})
    pairs = d.get("pairs", {})
    if not isinstance(pairs, dict):  # pre-cooldown logs kept a daily mac list
        pairs = {}
    if d.get("date") != _today():
        # the day rolls the CAP counter only; pair cooldowns are wall-clock
        # and survive midnight, or a 23:00 vonk would re-arm at 00:00
        return {"date": _today(), "pairs": pairs, "count": 0}
    d["pairs"] = pairs
    return d


def vonk_count_today():
    return _vonk_log()["count"]


def record_snuffel(mac, naam, code):
    """A completed snuffel with peer `mac`. Writes the boekje page on a
    first-ever meeting; scores a vonk when the pair's 4h cooldown has passed
    (daily cap on top) — a vonk is a picknick, 2-5 hapjes of one kind; a
    repeat inside the vonk cooldown shares a single hapje at most once an
    hour per pair. Inside the hour the handshake still celebrates but pays
    nothing. Nothing is chosen: the handshake itself pays out.
    Returns {"new_friend", "vonk", "dag", "food", "amount"} —
    food None / amount 0 when the pair is fully cooled down."""
    prefs = SharedPreferences(_APP)
    vr = prefs.get_list("vrienden", [])
    new_friend = not any(f.get("mac") == mac for f in vr)
    dag = _today()
    e = prefs.edit()
    if new_friend:
        vr.append({"mac": mac, "naam": naam, "code": code, "dag": dag})
        e.put_list("vrienden", vr)
    log = _vonk_log()
    now = _now()
    pair = log["pairs"].get(mac, {})
    vonk = (
        now - pair.get("vonk", -SNF_VONK_COOLDOWN_S) >= SNF_VONK_COOLDOWN_S
        and log["count"] < VONK_DAY_CAP
    )
    picknick = (
        vonk or now - pair.get("food", -SNF_FOOD_COOLDOWN_S) >= SNF_FOOD_COOLDOWN_S
    )
    if vonk:
        log["count"] += 1
        pair["vonk"] = now
    if picknick:
        pair["food"] = now
    log["pairs"][mac] = pair
    e.put_dict("vonk", log)
    e.commit()
    food = random.choice(FOODS) if picknick else None
    amount = (random.randrange(2, 6) if vonk else 1) if picknick else 0
    if amount:
        add_food(food, amount)
    return {
        "new_friend": new_friend,
        "vonk": vonk,
        "dag": dag,
        "food": food,
        "amount": amount,
    }


# Vonk-geluk: the chance that one of the OTHER player's creatures introduces
# itself, weighted by rarity — commons spread eagerly, rares reluctantly,
# legendaries never on their own (GAME_DESIGN.md, Vonk-geluk).
_GELUK_PCT = {"norm": 45, "rare": 15, "leg": 0}


def roll_vonk_geluk(peer_roster):
    """Roll against the peer's roster; returns a creature id or None. Only
    creatures we don't already know can introduce themselves."""
    cands = [by_id(cid) for cid in peer_roster]
    cands = [c for c in cands if c and not is_caught(c["id"])]
    if not cands:
        return None
    c = random.choice(cands)
    if random.randrange(100) < _GELUK_PCT.get(c["rarity"], 0):
        return c["id"]
    return None


# ── plukken: per-badge spot reloads + the day stat ──────────────────────────
PLUK_RELOAD_S = 60 * 60  # a spot reloads for THIS badge in about an hour


def _pluk():
    d = SharedPreferences(_APP).get_dict("pluk", {})
    d.setdefault("spots", {})
    if d.get("date") != _today():
        d["date"] = _today()
        d["count"] = 0
    return d


def pluk_wait_s(bssid):
    """Seconds until this spot yields again for this badge (0 = ready)."""
    t = _pluk()["spots"].get(bssid)
    if t is None:
        return 0
    return max(0, PLUK_RELOAD_S - (_now() - int(t)))


def pluk_waits(bssids):
    """Reload seconds for many spots in ONE prefs read -> {bssid: seconds}.
    The plukscherm asks about every network in a scan, and SharedPreferences
    re-reads and re-parses the whole config file on every construction — so
    asking per spot cost one flash read per network, every tick."""
    spots = _pluk()["spots"]
    now = _now()
    return {
        b: max(0, PLUK_RELOAD_S - (now - int(spots[b]))) if b in spots else 0
        for b in bssids
    }


def spots_ready_count():
    """Previously visited spots that have reloaded — the home-card stat."""
    now = _now()
    return sum(1 for t in _pluk()["spots"].values() if now - int(t) >= PLUK_RELOAD_S)


def pluk_count_today():
    return _pluk()["count"]


def record_pluk(bssid, oogst):
    """Bank a harvest: start the spot's reload, add the yield, bump the day
    stat. `oogst` is {food: n}."""
    d = _pluk()
    d["spots"][bssid] = _now()
    d["count"] = d.get("count", 0) + 1
    SharedPreferences(_APP).edit().put_dict("pluk", d).commit()
    for food, n in oogst.items():
        if n > 0:
            add_food(food, n)
