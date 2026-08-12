# store.py — persistent state via MicroPythonOS SharedPreferences.
# Stored at data/com.enigmeta.foxhunt/config.json on both desktop and badge.
#
#   "caught"   : list of caught creature ids
#   "beast"    : dict {str(id): pet-state} — care stats per caught creature
#   "origins"  : dict {str(id): "vangst"|"spoor"|"pluk"|"start"|"bezoek"|
#                "debug"} — how a creature arrived (own find / vonk-geluk /
#                wild pluk encounter / startbeest / random visitor / debug
#                toggle); feeds the dossier lineage
#   "zelf"     : list of ids stamped zelf gevonden (re-found at the fox)
#   "voorraad" : dict {food: count} — the finite pantry
#   "vrienden" : list of {mac, naam, code, dag} — the vriendenboekje
#   "vonk"     : snuffel log — {date, count (daily reset), pairs: {mac:
#                {vonk: epoch, food: epoch}}} — pair cooldown timestamps
#   "pluk"     : {spots: {bssid: epoch}, phase, count, creature_spots: []} —
#                hourly food reloads + one creature roll per spot/camp phase
#   "visitor"  : {started, slot, pending, pending_slot, debug, debug_due,
#                cooldown} — scheduled fallback meetings for verzamelaars
#   "outbox"   : list of queued badge→server reports (registrar.flush drains it)
#
# pet.py owns the rules (pure); this module owns persistence + the wall-clock.

import random

from mpos import SharedPreferences
import mpos.time
import pet
from creatures import CREATURES, by_id

_APP = "com.enigmeta.foxhunt"
_PLACE = "Fri3d Camp"  # stub: no GPS yet — see fox_radio for the backend seam


def _now():
    return mpos.time.epoch_seconds()


def _clock_ok():
    """True once the wall clock is real (NTP has run — year >= 2026). Until
    then the badge thinks it is 2000-01-01: any daily/phase gate that rolls
    on a date comparison would see a "new day" on every unsynced boot and
    re-arm its once-per-day rules, and cooldown math against 2026 stamps
    goes wildly negative."""
    try:
        from mpos.time_zone import TimeZone

        return bool(TimeZone.time_is_set())
    except Exception:
        return True  # desktop or older OS: trust the host clock


def _today():
    lt = mpos.time.localtime()
    return "%04d-%02d-%02d" % (lt[0], lt[1], lt[2])


def today():
    """The wall-clock day, for callers that key daily rules on it (the
    plukplek yield formula, the vonk log)."""
    return _today()


def profile():
    """The hunter profile dict, or None before registration.
    Keys: name, head, accs, bg, badge_id, hunter_id (the raw HID number,
    spec §2.2, None until minted — registrar.hunter_label formats it),
    synced (True once the cloud server confirmed the save)."""
    p = SharedPreferences(_APP).get_dict("profile", None)
    if p:
        # A profile saved by an older build holds the display label
        # ("JGR-0042") instead of the number. Readers get the number either
        # way; the string stays on flash until hunter_id is next written.
        hid = p.get("hunter_id")
        if isinstance(hid, str):
            try:
                p["hunter_id"] = int(hid[4:] if hid.startswith("JGR-") else hid)
            except ValueError:
                p["hunter_id"] = None
    return p if p else None


def save_profile(p):
    p.setdefault("since", _now())  # registration day, for the DAGEN stat
    SharedPreferences(_APP).edit().put_dict("profile", p).commit()


def clear_profile():
    """Forget the profile the badge was in the middle of building.

    Registration saves locally BEFORE the server round trip, on purpose: a
    server that never answers must not cost the player the maatje they just
    built ("je profiel is bewaard - probeer straks opnieuw"). That trade only
    holds while the badge is the sole claimant. When the server answers "this
    badge already has an account", the flow stops being a save and becomes a
    question (screen_reg_send._build_exists), and walking away is not one of
    its two answers. Leaving the half-built profile behind would open the badge
    on the home screen as a jager the server never heard of — and point ALLES
    WISSEN at an account belonging to whoever really registered.

    Editor has no remove(key), and profile() reads empty as None, so the way to
    forget a key here is to write it empty.
    """
    SharedPreferences(_APP).edit().put_dict("profile", {}).commit()


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
    # Session state resets too: the 1111 test code must not stay armed into
    # the next player's game — ALLES WISSEN hands the badge on without an
    # app restart, so the module flag survives unless somebody disarms it.
    disable_debug_code()


# ── Debug-code switch (formerly debug_unlock.py; merged for block economy) ──
# The debug screen itself opens from settings (five taps on the badge id);
# this is only the session-wide flag that screen makes the keypad honour.

DEBUG_CODE = "1111"
_debug_code_enabled = False


def enable_debug_code():
    global _debug_code_enabled
    _debug_code_enabled = True


def disable_debug_code():
    global _debug_code_enabled
    _debug_code_enabled = False


def debug_code_enabled():
    return _debug_code_enabled


def accepts_debug_code(code):
    return _debug_code_enabled and code == DEBUG_CODE


# App settings (the instellingen screen).
# led is the NeoPixel duty in percent; full brightness is blinding on the
# badge, so the default sits low. The settings screen steps it on a roughly
# doubling ladder (see _LED_STEPS) because the eye is power-law, not linear.
_DEFAULT_SETTINGS = {
    "geluid": True,
    "led": 30,
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


def debug_cheat(name):
    """Debug-screen cheats ("pluk_any", "nooit_moe"). Their own key, NOT part
    of settings: settings survive ALLES WISSEN (_KEEP_ON_RESET) because volume
    and brightness belong to the badge, but an armed cheat belongs to the
    player who armed it — hiding in the one preserved key handed the next
    player free play and pluk-anywhere. This key is wiped by default."""
    return bool(SharedPreferences(_APP).get_dict("debug", {}).get(name))


def set_debug_cheat(name, value):
    prefs = SharedPreferences(_APP)
    d = prefs.get_dict("debug", {})
    d[name] = bool(value)
    prefs.edit().put_dict("debug", d).commit()


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
    yourself — hunt, code), "spoor" (a vonk-geluk introduction), "pluk" (a
    wild encounter while foraging) or "start" (the startbeest granted at
    registration). Pure lineage data for the dossier; it gates nothing."""
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


def restore_caught(ids, self_found=None):
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
    zelf = prefs.get_list("zelf", [])
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
    for cid in self_found or []:
        if by_id(cid) and cid in have and cid not in zelf:
            zelf.append(cid)
            changed = True
    if changed:
        e.put_list("caught", have)
        e.put_list("zelf", zelf)
    e.commit()
    return have


def remove_caught(cid):
    """Forget a catch completely (debug/test support): pet state, origin and
    the zelf-gevonden stamp too — a debug re-add must start from nothing, not
    inherit a gold dossier stamp from the catch it replaced."""
    prefs = SharedPreferences(_APP)
    ids = prefs.get_list("caught", [])
    e = prefs.edit()
    if cid in ids:
        ids.remove(cid)
        e.put_list("caught", ids)
    zelf = prefs.get_list("zelf", [])
    if cid in zelf:
        zelf.remove(cid)
        e.put_list("zelf", zelf)
    origins = prefs.get_dict("origins", {})
    if str(cid) in origins:
        del origins[str(cid)]
        e.put_dict("origins", origins)
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


def zelf_ids():
    """Ids stamped zelf gevonden — the dossier's reader."""
    return SharedPreferences(_APP).get_list("zelf", [])


def zelf_gevonden(cid):
    """A jager found the fox of a creature already in the boek (screen_code).
    Not a dud but an upgrade (GAME_DESIGN.md, Zelf vinden): bump sightings,
    stamp the dossier, and pay the verzorgingspakket — hapjes weighted toward
    the creature's favourite. Nothing is removed or reset; bond and pet state
    carry straight through. Returns the pakket {food: n}.
    One instance, one editor (CLAUDE.md, Conventions)."""
    if cid in zelf_ids():
        return None
    v = voorraad()  # may seed the starter — must run BEFORE prefs snapshots
    prefs = SharedPreferences(_APP)
    e = prefs.edit()
    raw = prefs.get_dict("beast", {}).get(str(cid))
    if raw is not None:
        raw = dict(raw)
        raw["sightings"] = int(raw.get("sightings", 1)) + 1
        e.put_dict_item("beast", str(cid), raw)
    zelf = prefs.get_list("zelf", [])
    zelf.append(cid)
    e.put_list("zelf", zelf)
    c = by_id(cid)
    fav = (c.get("favoriet") if c else None) or FOODS[0]
    pakket = {fav: 2, random.choice([f for f in FOODS if f != fav]): 1}
    for f, n in pakket.items():
        v[f] = v.get(f, 0) + n
    e.put_dict("voorraad", v)
    e.commit()
    return pakket


def finished_ids():
    """Ids of beste vrienden (bond maxed). Raw read, no decay pass: bond
    never decays, so the stored value is already the truth — and the home
    grid asks per tile, where a decay-persist would cost a flash write each."""
    beasts = SharedPreferences(_APP).get_dict("beast", {})
    return {int(k) for k, v in beasts.items() if pet.finished(v)}


def band_total():
    """Sum of band levels across the caught roster — the profile's BAND stat.
    One raw prefs read, no decay pass, no writes: bond never decays (same
    rule as finished_ids), and the profile screen asks for the whole roster
    on every resume — 22 beast_state() calls meant 22 whole-file parses AND
    22 whole-file flash writes just to draw a number."""
    prefs = SharedPreferences(_APP)
    beasts = prefs.get_dict("beast", {})
    total = 0
    for cid in prefs.get_list("caught", []):
        st = beasts.get(str(cid))
        # unseeded legacy catch: fresh state, bond 10 -> level 1
        total += pet.level(int(st.get("bond", 10))) if st else 1
    return total


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
    if ok and pet.finished(state) and not pet.finished(raw):
        _report_bonded()
    return state, ok, msg, is_fav


def play_cost(cost, state=None):
    """What a beestenschool session really costs in energy segments — the
    tile's price normally, zero for a beste vriend or while the debug
    ONVERMOEIBAAR switch is on.

    Three places gate on energy (the school's tiles, the game's NOG EEN KEER,
    do_play itself) and they all ask here, so the switch can never leave one
    of them refusing while another lets you in. A beste vriend earns no more
    band (pet.play); the debug switch still suspends only the price, not the
    reward, and like every debug path it never leaves the badge."""
    return (
        0
        if (state is not None and pet.finished(state)) or debug_cheat("nooit_moe")
        else cost
    )


def do_play(cid, cost, favourite):
    """A beestenschool session; persist; return (state, ok, msg)."""
    prefs = SharedPreferences(_APP)
    raw = _raw_state(prefs, cid)
    if raw is None:
        return None, False, ""
    state = pet.decay(raw, _now())
    state, ok, msg = pet.play(state, play_cost(cost, state), favourite, _now())
    prefs.edit().put_dict_item("beast", str(cid), state).commit()
    if ok and pet.finished(state) and not pet.finished(raw):
        _report_bonded()
    return state, ok, msg


def _report_bonded():
    """The moment a beste vriend is born: queue the new bonded count for the
    server (scoreboard display only — GAME_DESIGN.md, What bond buys)."""
    enqueue_report("bonded", {"bonded": len(finished_ids())})


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
    return add_foods((food,) * n)


def add_foods(picks):
    """Bank a whole handful of hapjes in ONE write.

    Every commit rewrites config.json to flash, and that is the expensive half
    of banking a hapje — not the counting, not the parsing. The mini-games
    therefore collect a round's worth and hand the list over at a moment the
    player is not mid-jump (see GameActivity.take_treat); a commit per hapje
    stalled the 50 ms game tick long enough to see."""
    v = voorraad()
    for food in picks:
        v[food] = v.get(food, 0) + 1
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


# ── outbox: badge→server reports, queued until WiFi actually works ──────────
# Woods WiFi is spotty, so nothing badge→server ever blocks a screen: writers
# enqueue, registrar.flush() drains from natural moments (home resume). Survives
# reboots; ALLES WISSEN wipes it with everything else player-owned.


def outbox():
    return SharedPreferences(_APP).get_list("outbox", [])


def enqueue_report(kind, data):
    """Queue a badge→server report. kind: "snuffel" | "pluk" | "visitor" |
    "bonded" | "profile" — registrar._ROUTES maps kinds to routes. Callers enqueue LAST
    in their write path (the one-instance-one-editor rule: this commits via its
    own instance)."""
    prefs = SharedPreferences(_APP)
    box = prefs.get_list("outbox", [])
    box.append({"kind": kind, "data": data, "t": _now()})
    # Bounded: SharedPreferences re-parses the whole config on every
    # construction and Editor deep-copies it per commit, so an offline
    # weekend's unbounded queue would tax every feed and every toggle. 200
    # is far above a busy day's report count; beyond it the oldest reports
    # are the ones least likely to still matter.
    if len(box) > 200:
        box = box[-200:]
    prefs.edit().put_list("outbox", box).commit()


def outbox_pop():
    """Drop the head report (delivered, or refused forever)."""
    prefs = SharedPreferences(_APP)
    box = prefs.get_list("outbox", [])
    if box:
        prefs.edit().put_list("outbox", box[1:]).commit()


# ── random visitors: a safe collection floor for verzamelaars ─────────────
# Three broad, seeded windows spread meetings over a busy camp weekend. The
# badge owns the schedule so a bad network cannot make the fallback disappear;
# successful real meetings ride the outbox so account restore keeps the beest.
_VISITOR_WINDOWS_H = ((2, 4), (18, 26), (38, 48))
_VISITOR_FLOORS = (2, 3, 4)  # total collection size, including the startbeest
_VISITOR_COOLDOWN_S = 6 * 60 * 60
_CAMP_START = 1786021200  # Thu 2026-08-06 15:00 Europe/Brussels
_CAMP_END = 1786280400  # Sun 2026-08-09 15:00 Europe/Brussels


def visitor_due_at(started, badge_id, slot):
    """Seed one visitor time inside its broad post-registration window."""
    lo_h, hi_h = _VISITOR_WINDOWS_H[slot]
    span_s = (hi_h - lo_h) * 60 * 60
    seed = "%s|visitor|%d" % (badge_id.strip().lower(), slot)
    offset = _pluk_hash(seed) % (span_s + 1)
    return int(started) + lo_h * 60 * 60 + offset


def visitor_creature_for(badge_id, slot, have):
    """Pick an unknown base-tier visitor deterministically.

    The base-only pool is deliberate and is also enforced by the server. A
    random meeting can therefore never become a legendary grant, even if this
    local function or its caller is bypassed.
    """
    known = set(have)
    cands = [c for c in CREATURES if c["rarity"] == "norm" and c["id"] not in known]
    if not cands:
        return None
    seed = "%s|visitor-creature|%s" % (badge_id.strip().lower(), slot)
    return cands[_pluk_hash(seed) % len(cands)]["id"]


def _visitor():
    d = SharedPreferences(_APP).get_dict("visitor", {})
    p = profile() or {}
    since = p.get("since")
    if since is None:
        since = _now()
    since = int(since)
    d.setdefault("started", max(since, _CAMP_START))
    d.setdefault("slot", 0)
    d.setdefault("pending", None)
    d.setdefault("pending_slot", None)
    d.setdefault("debug", False)
    d.setdefault("debug_due", 0)
    d.setdefault("cooldown", 0)
    return d


def _save_visitor(d):
    SharedPreferences(_APP).edit().put_dict("visitor", d).commit()


def schedule_debug_visitor(delay_s=10):
    """Make a local-only visitor due after delay_s; return its due epoch."""
    d = _visitor()
    d["debug_due"] = _now() + int(delay_s)
    _save_visitor(d)
    return d["debug_due"]


def visitor_pending():
    """Return the visitor currently waiting, or create a due one.

    Merely checking never awards anything. A pending visitor is durable and
    survives becoming a jager; only creating future normal visits is disabled
    for jagers. Debug meetings bypass timing/mode but never server sync.
    """
    p = profile()
    if not p:
        return None
    d = _visitor()
    have = caught_ids()
    badge = p.get("badge_id", "")

    pending = d.get("pending")
    if pending is not None:
        if pending not in have:
            return pending
        # It arrived through another route before the player opened the visit.
        # .get with a default is not enough here: _visitor() setdefaults the
        # key to None, so it always exists — test the VALUE.
        slot = d.get("pending_slot")
        if slot is None:
            slot = d.get("slot", 0)
        replacement = visitor_creature_for(badge, slot, have)
        if replacement is not None:
            d["pending"] = replacement
            _save_visitor(d)
            return replacement
        d["pending"] = None
        d["pending_slot"] = None
        d["debug"] = False
        _save_visitor(d)
        return None

    now = _now()
    if d.get("debug_due", 0) and now >= int(d["debug_due"]):
        cid = visitor_creature_for(badge, "debug-%d" % int(d["debug_due"]), have)
        d["debug_due"] = 0
        if cid is not None:
            d["pending"] = cid
            d["pending_slot"] = -1
            d["debug"] = True
        _save_visitor(d)
        return cid

    if p.get("hunter_id") or now < int(d.get("cooldown", 0)):
        return None

    slot = int(d.get("slot", 0))
    while slot < len(_VISITOR_WINDOWS_H):
        due = visitor_due_at(d["started"], badge, slot)
        if due > _CAMP_END:
            d["slot"] = len(_VISITOR_WINDOWS_H)
            _save_visitor(d)
            return None
        if now < due:
            return None
        if len(have) >= _VISITOR_FLOORS[slot]:
            slot += 1
            d["slot"] = slot
            _save_visitor(d)
            continue
        cid = visitor_creature_for(badge, slot, have)
        if cid is None:
            d["slot"] = len(_VISITOR_WINDOWS_H)
            _save_visitor(d)
            return None
        d["pending"] = cid
        d["pending_slot"] = slot
        d["debug"] = False
        _save_visitor(d)
        return cid
    return None


def claim_visitor():
    """Award the waiting visitor and queue a durable report for real visits."""
    d = _visitor()
    cid = d.get("pending")
    if cid is None:
        return None
    c = by_id(cid)
    if c is None or c["rarity"] != "norm":
        # Corrupt state must fail closed: especially never turn into a
        # legendary award merely because a debug save was hand-edited.
        d["pending"] = None
        d["pending_slot"] = None
        d["debug"] = False
        _save_visitor(d)
        return None

    # The key always exists (setdefault None in _visitor), so int() on the
    # .get default would raise TypeError on a pre-pending_slot save — right
    # in the visit that is the collector's safety net.
    slot = d.get("pending_slot")
    slot = int(slot) if slot is not None else int(d.get("slot", 0))
    debug = bool(d.get("debug"))
    d["pending"] = None
    d["pending_slot"] = None
    d["debug"] = False
    if not debug:
        d["slot"] = max(int(d.get("slot", 0)), slot + 1)
        d["cooldown"] = _now() + _VISITOR_COOLDOWN_S
    _save_visitor(d)

    add_caught(cid, origin="bezoek")
    if not debug:
        enqueue_report("visitor", {"slot": slot, "creature_id": cid})
    return cid


# ── snuffelen: vrienden (permanent) + vonken (cooldown-gated) ───────────────
# The vriendenboekje never decays. The vonk log holds per-pair timestamps:
# a pair scores a new vonk after 6h, and shares picknick
# food after ~1h — inside the hour a repeat snuffel pays NOTHING, so two
# badges cannot be farmed for food. Identity is the peer's MAC (snuffel_link)
# or a manual code — either way one string.
SNF_VONK_COOLDOWN_S = 6 * 60 * 60
SNF_FOOD_COOLDOWN_S = 60 * 60


def vrienden():
    return SharedPreferences(_APP).get_list("vrienden", [])


def _vonk_log():
    d = SharedPreferences(_APP).get_dict("vonk", {})
    pairs = d.get("pairs", {})
    if not isinstance(pairs, dict):  # pre-cooldown logs kept a daily mac list
        pairs = {}
    if d.get("date") != _today() and (_clock_ok() or d.get("date") is None):
        # the day rolls the display counter only; pair cooldowns are wall-clock
        # and survive midnight, or a 23:00 vonk would re-arm at 00:00.
        # An unsynced clock (2000-01-01) is not a new day — rolling on it
        # would corrupt the daily display count on every pre-NTP boot.
        return {"date": _today(), "pairs": pairs, "count": 0}
    d["pairs"] = pairs
    return d


def vonk_count_today():
    return _vonk_log()["count"]


def record_snuffel(mac, naam, code):
    """A completed snuffel with peer `mac`. Writes the boekje page on a
    first-ever meeting and refreshes its name and companion on every later
    meeting; scores a vonk when the pair's 6h cooldown has passed — a vonk is
    a picknick, 2-5 hapjes of one kind; a repeat inside
    the vonk cooldown shares a single hapje at most once an hour per pair.
    Inside the hour the handshake still celebrates but pays nothing. Nothing
    is chosen: the handshake itself pays out.
    Returns {"new_friend", "vonk", "dag", "food", "amount"} —
    food None / amount 0 when the pair is fully cooled down."""
    prefs = SharedPreferences(_APP)
    vr = prefs.get_list("vrienden", [])
    friend = None
    for f in vr:
        if f.get("mac") == mac:
            friend = f
            break
    new_friend = friend is None
    dag = _today()
    e = prefs.edit()
    if new_friend:
        vr.append({"mac": mac, "naam": naam, "code": code, "dag": dag})
        e.put_list("vrienden", vr)
    elif friend.get("naam") != naam or friend.get("code") != code:
        friend["naam"] = naam
        friend["code"] = code
        e.put_list("vrienden", vr)
    log = _vonk_log()
    now = _now()
    pair = log["pairs"].get(mac, {})
    vonk = (
        now - pair.get("vonk", -SNF_VONK_COOLDOWN_S) >= SNF_VONK_COOLDOWN_S
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
        "at": now,
        "food": food,
        "amount": amount,
    }


def shareable_roster(roster, self_found, is_hunter):
    """The ids this player may advertise as possible outgoing introductions.

    Base creatures can always travel onward. Gatherers may pass rare creatures
    onward, but hunters must first find a rare themselves. A legendary is
    advertised only by the hunter who personally found it; a gatherer who
    received one is an endpoint and therefore never puts it in the shareable
    set.
    """
    zelf = set(self_found)
    result = []
    for cid in roster:
        c = by_id(cid)
        if not c:
            continue
        if c["rarity"] == "norm":
            result.append(cid)
        elif c["rarity"] == "rare" and (not is_hunter or cid in zelf):
            result.append(cid)
        elif c["rarity"] == "leg" and is_hunter and cid in zelf:
            result.append(cid)
    return result


def select_vonk_creature(
    sender_shareable,
    recipient_roster,
    encounter_key,
    giver_key,
    recipient_key,
    receiver_is_hunter,
):
    """Choose one guaranteed eligible introduction in a single direction.

    Each direction resolves independently. No candidate means generated food,
    never failure of the other direction. Both badges derive the same choice
    from the shared encounter and directed badge ids.
    """
    known = {cid for cid in recipient_roster if by_id(cid)}
    candidates = []
    for cid in sender_shareable:
        c = by_id(cid)
        if not c or cid in known:
            continue
        if c["rarity"] == "leg" and receiver_is_hunter:
            continue
        candidates.append(cid)
    candidates.sort()
    if not candidates:
        return None
    seed = "%s|%s>%s" % (encounter_key, giver_key, recipient_key)
    return candidates[_pluk_hash(seed) % len(candidates)]


# ── plukken: hourly food + one creature roll per camp phase ─────────────────
PLUK_RELOAD_S = 60 * 60  # a spot reloads for THIS badge in about an hour

# Plukken can introduce base creatures only. Rare and legendary creatures
# enter through LoRa hunts and eligible snuffel introductions.
_PLUK_OPPORTUNITY_PERMILLE = 400
_PLUK_GELUK_PERMILLE = {"norm": 450}


def _previous_date(year, month, day):
    """Calendar day before (year, month, day), without datetime (MicroPython)."""
    if day > 1:
        return year, month, day - 1
    if month == 1:
        return year - 1, 12, 31
    month -= 1
    days = (
        31,
        29 if year % 4 == 0 and (year % 100 != 0 or year % 400 == 0) else 28,
        31,
        30,
        31,
        30,
        31,
        31,
        30,
        31,
        30,
        31,
    )
    return year, month, days[month - 1]


def _pluk_phase_for(local):
    """The 15:00-to-15:00 camp day containing a local-time tuple.

    Fri3d runs Thursday 15:00 through Sunday 15:00: shifting the day boundary
    to 15:00 produces exactly three phases, despite spanning four calendar
    dates. The generic date label also keeps emulator/dev plukken useful after
    camp instead of hard-coding a one-weekend kill switch.
    """
    year, month, day, hour = local[:4]
    if hour < 15:
        year, month, day = _previous_date(year, month, day)
    return "%04d-%02d-%02d" % (year, month, day)


def pluk_phase():
    return _pluk_phase_for(mpos.time.localtime())


def _pluk_hash(text):
    """Stable FNV-1a — Python's hash is neither stable nor on every badge."""
    h = 0x811C9DC5
    for b in text.encode():
        h ^= b
        h = (h * 0x01000193) & 0xFFFFFFFF
    return h


def pluk_creature_for(badge_id, bssid, phase, have):
    """Deterministic wild encounter for one badge/spot/camp phase.

    Returns a creature id or None. Like vonk-geluk, the candidate comes only
    from creatures the player does not know and then passes a rarity-weighted
    chance. Badge id is part of the seed: a legendary is a personal discovery,
    not one globally lucky AP that becomes a queue when somebody talks.
    """
    seed = "%s|%s|%s" % (badge_id.strip().lower(), bssid.strip().lower(), phase)
    if _pluk_hash(seed + "|opportunity") % 1000 >= _PLUK_OPPORTUNITY_PERMILLE:
        return None
    known = set(have)
    cands = [
        c for c in CREATURES if c["rarity"] == "norm" and c["id"] not in known
    ]
    if not cands:
        return None
    c = cands[_pluk_hash(seed + "|candidate") % len(cands)]
    chance = _PLUK_GELUK_PERMILLE.get(c["rarity"], 0)
    if _pluk_hash(seed + "|chance") % 1000 < chance:
        return c["id"]
    return None


def _pluk():
    d = SharedPreferences(_APP).get_dict("pluk", {})
    d.setdefault("spots", {})
    phase = pluk_phase()
    # Same clock gate as _vonk_log: a pre-NTP boot reads phase "1999-12-31",
    # and rolling on it would re-arm every spot's once-per-camp-phase
    # creature roll — with a genuinely different seed, so a new roll, not a
    # repeat.
    if d.get("phase") != phase and (_clock_ok() or d.get("phase") is None):
        d["phase"] = phase
        d["count"] = 0
        d["creature_spots"] = []
    d.setdefault("creature_spots", [])
    return d


def pluk_wait_s(bssid):
    """Seconds until this spot yields again for this badge (0 = ready).
    Clamped to one full reload: a clock that regressed (pre-NTP boot reading
    2000 against 2026 stamps) would otherwise report a ~26-year wait."""
    t = _pluk()["spots"].get(bssid)
    if t is None:
        return 0
    return min(PLUK_RELOAD_S, max(0, PLUK_RELOAD_S - (_now() - int(t))))


def pluk_waits(bssids):
    """Reload seconds for many spots in ONE prefs read -> {bssid: seconds}.
    The plukscherm asks about every network in a scan, and SharedPreferences
    re-reads and re-parses the whole config file on every construction — so
    asking per spot cost one flash read per network, every tick."""
    spots = _pluk()["spots"]
    now = _now()
    return {
        b: min(PLUK_RELOAD_S, max(0, PLUK_RELOAD_S - (now - int(spots[b]))))
        if b in spots
        else 0
        for b in bssids
    }


def spots_ready_count():
    """Previously visited spots that have reloaded — the home-card stat."""
    now = _now()
    return sum(1 for t in _pluk()["spots"].values() if now - int(t) >= PLUK_RELOAD_S)


def pluk_count_today():
    return _pluk()["count"]


def record_pluk(bssid, oogst):
    """Bank food and, once per spot/camp phase, its wild-creature roll.

    Returns the new creature id or None. The attempt is persisted even when it
    misses, so an hourly food reload cannot reroll it. A success is queued for
    the server last, after every local write, so restore can hand it back.
    """
    bssid = bssid.lower()
    d = _pluk()
    d["spots"][bssid] = _now()
    d["count"] = d.get("count", 0) + 1
    geluk = None
    if bssid not in d["creature_spots"]:
        d["creature_spots"].append(bssid)
        p = profile() or {}
        geluk = pluk_creature_for(
            p.get("badge_id", ""), bssid, d["phase"], caught_ids()
        )
    SharedPreferences(_APP).edit().put_dict("pluk", d).commit()
    for food, n in oogst.items():
        if n > 0:
            add_food(food, n)
    if geluk is not None:
        add_caught(geluk, origin="pluk")
        enqueue_report(
            "pluk",
            {"bssid": bssid, "phase": d["phase"], "creature_id": geluk},
        )
    return geluk
