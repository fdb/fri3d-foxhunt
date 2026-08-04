# store.py — persistent state via MicroPythonOS SharedPreferences.
# Stored at data/be.fri3d.foxhunt/config.json on both desktop and badge.
#
#   "caught" : list of caught creature ids
#   "beast"  : dict {str(id): pet-state} — care stats per caught creature
#
# pet.py owns the rules (pure); this module owns persistence + the wall-clock.

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


# App settings (the instellingen screen). trillen is stored but drives
# nothing yet (no vibration hardware API) — it gates that when it lands.
# led is the NeoPixel duty in percent; full brightness is blinding on the
# badge, so the default sits low. The settings screen steps it on a roughly
# doubling ladder (see _LED_STEPS) because the eye is power-law, not linear.
_DEFAULT_SETTINGS = {"geluid": True, "trillen": False, "led": 30}


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


def add_caught(cid):
    prefs = SharedPreferences(_APP)
    ids = prefs.get_list("caught", [])
    e = prefs.edit()
    if cid not in ids:
        ids.append(cid)
        e.put_list("caught", ids)
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
    """Feed a hapje ('bes'|'noot'|'eikel'); persist; (state, ok, msg, is_fav)."""
    prefs = SharedPreferences(_APP)
    raw = _raw_state(prefs, cid)
    if raw is None:
        return None, False, "", False
    c = by_id(cid)
    favoriet = c.get("favoriet") if c else None
    state, ok, msg, is_fav = pet.feed(pet.decay(raw, _now()), food, favoriet, _now())
    prefs.edit().put_dict_item("beast", str(cid), state).commit()
    return state, ok, msg, is_fav
