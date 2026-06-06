# store.py — persistent "caught" set, via MicroPythonOS SharedPreferences.
# Stored at data/com.fri3d.beestenjacht/config.json on both desktop and badge.

from mpos import SharedPreferences

_APP = "com.fri3d.beestenjacht"


def caught_ids():
    return SharedPreferences(_APP).get_list("caught", [])


def is_caught(cid):
    return cid in caught_ids()


def add_caught(cid):
    prefs = SharedPreferences(_APP)
    ids = prefs.get_list("caught", [])
    if cid not in ids:
        ids.append(cid)
        prefs.edit().put_list("caught", ids).commit()
