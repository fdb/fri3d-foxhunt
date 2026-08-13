# companion.py — the hunter's companion ("maatje" in the UI): a head,
# stackable accessories and a backdrop colour, picked during registration.
#
# Every layer is a 16x16 PNG exported from artwork/companions/companion.aseprite,
# one file per Aseprite layer, baked into the sprite atlas. The invariant that
# keeps that honest:
#
#     aseprite layer name  ==  id here  ==  atlas key "companions/<id>.png"
#
# so nothing has to carry a filename around. Rename an id and you must rename
# the layer and re-run scripts/bake_sprites.sh.
#
# All fifteen layers were drawn on one shared face in one document, so an
# accessory drops onto any head unshifted — no per-head anchoring.

import lvgl as lv
import art
import ui

HEADS = [
    {"id": "vos", "naam": "Vos"},
    {"id": "uil", "naam": "Uil"},
    {"id": "beer", "naam": "Beer"},
    {"id": "konijn", "naam": "Konijn"},
    {"id": "varken", "naam": "Varken"},
    {"id": "leeuw", "naam": "Leeuw"},
    {"id": "zeemeeuw", "naam": "Meeuw"},
    {"id": "kikker", "naam": "Kermit"},
    {"id": "zeehond", "naam": "Siel"},
    {"id": "pinguin", "naam": "Ping"},
    {"id": "ijsbeer", "naam": "Knut"},
    {"id": "muis", "naam": "Jerry"},
    {"id": "eekhoorn", "naam": "Babbel"},
    {"id": "axolotl", "naam": "Axel"},
]

# ORDER IS DRAW ORDER, bottom-up — the same stacking the artist used in the
# .aseprite. That is why kroon sits over bril and sterren over everything.
#
# unlock: creatures caught before it opens up. The three freebies are what you
# build your first maatje from; the other seven arrive one per two catches
# (2, 4, ... 14), so completing the accessory roster is achievable in a
# weekend while still rewarding steady progress.
ACCS = [
    {"id": "bril", "naam": "Bril", "unlock": 0},
    {"id": "strik", "naam": "Strik", "unlock": 0},
    {"id": "hoed", "naam": "Hoed", "unlock": 0},
    {"id": "bloem", "naam": "Bloem", "unlock": 2},
    {"id": "sjaal", "naam": "Sjaal", "unlock": 4},
    {"id": "pet", "naam": "Pet", "unlock": 6},
    {"id": "koptelefoon", "naam": "Koptel.", "unlock": 8},
    {"id": "snor", "naam": "Snor", "unlock": 10},
    {"id": "kroon", "naam": "Kroon", "unlock": 12},
    # "Ster", not "Sterren": a tile label is 38px wide and the plural clips.
    {"id": "sterren", "naam": "Ster", "unlock": 14},
]

# backdrop swatches; the last one is the single dark option.
BGS = [0xE9F1CF, 0xF7F0DF, 0xEFE0BB, 0xCFE0EA, 0xF0D3D6, 0xDED3EA, 0x3A4A34]

# ── Wire format: the companion as a 9-char shortcode ──────────────────────────
#
#   H01A003C1   =  head 1, accessories bril+strik, backdrop 1
#   ^--^ ^^^^ ^
#    |   |  | +-- C: 1-based index into BGS
#    |   |  +---- A: 12-bit accessory mask, three HEX digits
#    +---+------- H: zero-padded, 1-based index into HEADS
#
# The server stores this in players.profile_pic. It exists because the badge's
# own head/accs/bg lists don't survive a wipe — the shortcode is what the
# restore flow gets back, and the only thing that makes a recovered profile
# look like the player's own companion instead of a default fox.
#
# Indices are 1-based so a 0 can never be mistaken for "unset". The mask is hex
# rather than decimal because 10 accessories need more than the 10 bits three
# decimal digits would give once a single one is added; 12 bits leaves two
# spare slots.
#
# BIT POSITIONS ARE APPEND-ONLY: bit i is ACCS[i], so a new accessory goes at
# the END of the list. Inserting one in the middle silently rewrites every
# shortcode already stored on the server — and because ACCS order is also draw
# order, "append-only" and "draw on top" are now the same constraint: a new
# accessory joins above sterren, or the wire format breaks.
_ACCS_WIRE = [a["id"] for a in ACCS]

_DEFAULT_COMPANION = (HEADS[0]["id"], [], 0)


def encode(head_id, accs, bg):
    """(head id, accessory ids, backdrop index) -> "H01A003C1"."""
    h = 1
    for i, x in enumerate(HEADS):
        if x["id"] == head_id:
            h = i + 1
            break
    mask = 0
    for i, aid in enumerate(_ACCS_WIRE):
        if aid in accs:
            mask |= 1 << i
    c = bg + 1 if 0 <= bg < len(BGS) else 1
    return "H%02dA%03XC%d" % (h, mask, c)


def decode(code):
    """ "H01A003C1" -> (head id, accessory ids, backdrop index).

    Anything malformed or out of range falls back to the default companion: a
    profile that renders beats an error dialog halfway through a restore, and
    an old badge reading a code from a newer roster is a case we'd rather
    degrade than refuse. The old one-digit H1...H9 form remains readable so
    profiles already stored on the server survive this format upgrade."""
    try:
        if len(code) == 9 and code[0] == "H" and code[3] == "A" and code[7] == "C":
            h = int(code[1:3])
            mask = int(code[4:7], 16)
            c = int(code[8])
        elif len(code) == 8 and code[0] == "H" and code[2] == "A" and code[6] == "C":
            h = int(code[1])
            mask = int(code[3:6], 16)
            c = int(code[7])
        else:
            return _DEFAULT_COMPANION
    except (TypeError, ValueError):
        return _DEFAULT_COMPANION
    head = HEADS[h - 1]["id"] if 1 <= h <= len(HEADS) else HEADS[0]["id"]
    accs = [aid for i, aid in enumerate(_ACCS_WIRE) if mask & (1 << i)]
    return head, accs, (c - 1 if 1 <= c <= len(BGS) else 0)


def head_by_id(hid):
    """Unknown ids fall back to the fox — a profile saved by an older roster
    (it had a kikker) must still render something."""
    for h in HEADS:
        if h["id"] == hid:
            return h
    return HEADS[0]


def src(part_id):
    """The atlas key for a head or accessory id (folder is plural on purpose:
    companion/ would shadow this module on import back when these were files,
    and the atlas keys kept the artwork paths)."""
    return "companions/" + part_id + ".png"


def is_unlocked(acc, caught_count):
    return caught_count >= acc["unlock"]


# One art pixel up, held, then back — a twinkle you notice without it ever
# pulling the eye off the portrait.
_TWINKLE_MS = 500


def _twinkle(layer, scale):
    """Make the sterren layer hop one source pixel, forever.

    An lv.anim_t rather than an lv.timer because LVGL kills an animation when
    its var is deleted (lv_obj.c drops them in the destructor) — the profile
    screen rebuilds itself on every resume, and a timer would outlive the
    widget it pokes. path_step holds each end instead of sliding between them,
    so the stars jump a whole pixel like pixel art should."""
    a = lv.anim_t()
    a.init()
    a.set_var(layer)
    a.set_values(0, -scale)
    a.set_duration(_TWINKLE_MS)
    a.set_reverse_duration(_TWINKLE_MS)
    a.set_repeat_count(lv.ANIM_REPEAT_INFINITE)
    a.set_path_cb(lv.anim_t.path_step)
    a.set_custom_exec_cb(lambda _a, v: layer.set_y(v))
    a.start()


def draw(parent, head_id, accs, scale, x=0, y=0, animate=False):
    """The composed companion: head layer + every accessory the player owns.

    Layers go down in ACCS order, never in the order they were picked, so the
    same set always stacks the same way. `animate` opts into the sterren
    twinkle — the portrait screens want it, a 32px header thumbnail doesn't.
    Returns the (transparent) wrapper box, 16*scale square."""
    px = 16 * scale
    wrap = ui.box(parent, x, y, px, px, None)
    art.sprite_img(wrap, src(head_by_id(head_id)["id"]), scale)
    for a in ACCS:
        if a["id"] not in accs:
            continue
        layer = art.sprite_img(wrap, src(a["id"]), scale)
        if animate and a["id"] == "sterren":
            _twinkle(layer, scale)
    return wrap
