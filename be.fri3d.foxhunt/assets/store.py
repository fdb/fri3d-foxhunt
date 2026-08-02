# store.py — persistent state via MicroPythonOS SharedPreferences.
# Stored at data/be.fri3d.foxhunt/config.json on both desktop and badge.
#
#   "caught" : list of caught creature ids
#   "beast"  : dict {str(id): pet-state} — companion stats per caught creature
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
_DEFAULT_SETTINGS = {"geluid": True, "trillen": False}


def settings():
    s = dict(_DEFAULT_SETTINGS)
    s.update(SharedPreferences(_APP).get_dict("settings", {}))
    return s


def set_setting(key, value):
    prefs = SharedPreferences(_APP)
    s = prefs.get_dict("settings", {})
    s[key] = value
    prefs.edit().put_dict("settings", s).commit()


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
    # First catch seeds the companion; a recatch never overwrites its stats.
    beast = prefs.get_dict("beast", {})
    if str(cid) not in beast:
        e.put_dict_item("beast", str(cid), pet.default_state(_today(), _PLACE, _now()))
    e.commit()


def remove_caught(cid):
    """Forget a catch and its companion state (debug/test support)."""
    prefs = SharedPreferences(_APP)
    ids = prefs.get_list("caught", [])
    e = prefs.edit()
    if cid in ids:
        ids.remove(cid)
        e.put_list("caught", ids)
    e.remove_dict_item("beast", str(cid))
    e.commit()


def _raw_state(prefs, cid):
    """The stored companion dict for cid, seeding a default for caught-but-
    unseeded creatures (legacy saves from before companions existed). Returns
    None only if the creature isn't caught at all."""
    raw = prefs.get_dict("beast", {}).get(str(cid))
    if raw is None and cid in prefs.get_list("caught", []):
        raw = pet.default_state(_today(), _PLACE, _now())
        prefs.edit().put_dict_item("beast", str(cid), raw).commit()
    return raw


def beast_state(cid):
    """Companion stats with time-decay applied and persisted. None if uncaught."""
    prefs = SharedPreferences(_APP)
    raw = _raw_state(prefs, cid)
    if raw is None:
        return None
    state = pet.decay(raw, _now())
    prefs.edit().put_dict_item("beast", str(cid), state).commit()
    return state


def do_action(cid, action):
    """Apply a companion action; persist; return (state, ok, message)."""
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
