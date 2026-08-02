# companion.py — the hunter's companion ("maatje" in the UI): a head,
# stackable accessories and a backdrop colour, picked during registration.
#
# Every sprite shares the head's 16x16 grid, so accessory layers drop straight
# onto any head. Accessories are authored on a reference face (eye line 7,
# mouth line 11) and shifted per head by its own eye/mouth line — one bril
# fits five koppen. Ported from the design bundle (mascotte.jsx).

import art
import ui

_E = "................"

# eye/mouth: the row the eyes / mouth sit on, for accessory anchoring.
HEADS = [
    {
        "id": "vos",
        "naam": "Vos",
        "shape": "fox",
        "pal": "orange",
        "eye": 8,
        "mouth": 11,
    },
    {
        "id": "uil",
        "naam": "Uil",
        "shape": "owl",
        "pal": "bluegrey",
        "eye": 6,
        "mouth": 11,
    },
    {
        "id": "beer",
        "naam": "Beer",
        "pal": "brown",
        "eye": 7,
        "mouth": 10,
        "rows": [
            "................",
            "..kkk......kkk..",
            ".kdddk....kdddk.",
            ".kdrrdk..kdrrdk.",
            ".kdrrrkkkkrrrdk.",
            "..kdrrrrrrrrdk..",
            "..krrrrrrrrrrk..",
            "..krweerrweerk..",
            "..krrrrrrrrrrk..",
            "..krrlllllllrk..",
            "..kdrlnnnnlrdk..",
            "..kdrlllllllrk..",
            "...kdrrrrrrdk...",
            "....kkddddkk....",
            "......kkkk......",
            "................",
        ],
    },
    {
        "id": "konijn",
        "naam": "Konijn",
        "pal": "cream",
        "eye": 8,
        "mouth": 11,
        "rows": [
            "...kk......kk...",
            "..kllk....kllk..",
            "..kllk....kllk..",
            "..kllk....kllk..",
            "..kkrkkkkkkrkk..",
            "..krrrrrrrrrrk..",
            ".krrrrrrrrrrrrk.",
            ".krweerrrrweerk.",
            ".krrrrrrrrrrrrk.",
            ".krrlllllllllrk.",
            ".kdrlnnllnnlrdk.",
            ".kdrlllllllllrk.",
            "..kdrrrrrrrrdk..",
            "...kkddddddkk...",
            ".....kkkkkk.....",
            "................",
        ],
    },
    {
        "id": "kikker",
        "naam": "Kikker",
        "pal": "green",
        "eye": 3,
        "mouth": 8,
        "rows": [
            "................",
            "...kkk....kkk...",
            "..kwwwkkkkwwwk..",
            ".kkweekkkkweekk.",
            ".krwwwrrrrwwwrk.",
            ".krrrrnrrnrrrrk.",
            "krrrrrrrrrrrrrrk",
            "krrrrrrrrrrrrrrk",
            "kddddddddddddddk",
            "krlllllllllllllk",
            "krlllllllllllllk",
            "kdlllllllllllldk",
            ".kdlllllllllldk.",
            "..kddddddddddk..",
            "....kkkkkkkk....",
            "................",
        ],
    },
]

# anchor: which facial line the accessory rides ("eye" | "mouth" | None=fixed).
# unlock: creatures caught before it opens up (0 = free from the start;
# "leg" = catch a legendary). At registration everything but 0 is locked.
ACCS = [
    {"id": "geen", "naam": "Geen", "unlock": 0},
    {
        "id": "bril",
        "naam": "Bril",
        "unlock": 0,
        "anchor": "eye",
        "pal": {"k": 0x34271A, "w": 0xDFF0F6},
        "rows": [_E] * 6
        + ["...kkkk..kkkk...", ".kkkwwkkkkwwkkk.", "...kkkk..kkkk..."]
        + [_E] * 7,
    },
    {
        "id": "snor",
        "naam": "Snor",
        "unlock": 0,
        "anchor": "mouth",
        "pal": {"m": 0x4A3320},
        "rows": [_E] * 10
        + ["....mmm..mmm....", "...mmmmmmmmmm...", "....mm....mm...."]
        + [_E] * 3,
    },
    {
        "id": "hoed",
        "naam": "Hoed",
        "unlock": 4,
        "pal": {"k": 0x241A12, "h": 0x4A3A5A, "b": 0xF0C64A},
        "rows": [
            ".....kkkkkk.....",
            "....khhhhhhk....",
            "....khhhhhhk....",
            "...kkkkkkkkkk...",
            "..kbbbbbbbbbbk..",
            "...kkkkkkkkkk...",
        ]
        + [_E] * 10,
    },
    {
        "id": "zonnebril",
        "naam": "Shades",
        "unlock": 7,
        "anchor": "eye",
        "pal": {"k": 0x241A12, "w": 0x4A4460},
        "rows": [_E] * 6
        + ["...kkkk..kkkk...", ".kkkwwkkkkwwkkk.", "...kkkk..kkkk..."]
        + [_E] * 7,
    },
    {
        "id": "koptel",
        "naam": "Koptel.",
        "unlock": 9,
        "pal": {"k": 0x1A2A3A, "h": 0x3A6A8A},
        "rows": [
            _E,
            ".....kkkkkk.....",
            "...kkhhhhhhkk...",
            "..kh........hk..",
            ".khh........hhk.",
            ".khh........hhk.",
            ".khh........hhk.",
            "..kk........kk..",
        ]
        + [_E] * 8,
    },
    {
        "id": "strik",
        "naam": "Strik",
        "unlock": 8,
        "pal": {"k": 0x7A3B50, "p": 0xE07A9A},
        "rows": [
            _E,
            "...kk....kk.....",
            "..kppk..kppk....",
            "..kpppkkkpppk...",
            "..kppk.k.kppk...",
            "...kk.kkk.kk....",
        ]
        + [_E] * 10,
    },
    {
        "id": "pleister",
        "naam": "Pleister",
        "unlock": 5,
        "anchor": "mouth",
        "pal": {"k": 0xA8794A, "p": 0xF6D3A8},
        "rows": [_E] * 9
        + ["..kkkkkk........", "..kppppk........", "..kkkkkk........"]
        + [_E] * 4,
    },
    {
        "id": "sjaal",
        "naam": "Sjaal",
        "unlock": 6,
        "pal": {"k": 0x5A1F14, "s": 0xC2452F, "t": 0xEFE0BB},
        "rows": [_E] * 11
        + [
            "..kssssssssssk..",
            "..ksttttttttsk..",
            "..kssssssssssk..",
            "....kssk........",
            "....kssk........",
        ],
    },
    {
        "id": "kroon",
        "naam": "Kroon",
        "unlock": 10,
        "pal": {"k": 0x34271A, "b": 0xF0C64A},
        "rows": [
            "....k..k..k.....",
            "...kbkkbkkbk....",
            "...kbbbbbbbk....",
            "...kkkkkkkkk....",
        ]
        + [_E] * 12,
    },
    {
        "id": "bloem",
        "naam": "Bloem",
        "unlock": 6,
        "pal": {"p": 0xE07A9A, "y": 0xF0C64A, "g": 0x5A9A3C, "k": 0x7A3B50},
        "rows": [
            _E,
            "..kpk...........",
            ".kpypk..........",
            "..kpk...........",
            "...g............",
            "...g............",
        ]
        + [_E] * 10,
    },
    {
        "id": "sterren",
        "naam": "Sterren",
        "unlock": "leg",
        "pal": {"b": 0xF0C64A, "k": 0xFFF7E6},
        "rows": [
            _E,
            "..b..........b..",
            ".bkb........bkb.",
            "..b..........b..",
        ]
        + [_E] * 8
        + [
            "..b..........b..",
            ".bkb........bkb.",
            "..b..........b..",
            _E,
        ],
    },
]

# backdrop swatches; the last one is the single dark option.
BGS = [0xE9F1CF, 0xF7F0DF, 0xEFE0BB, 0xCFE0EA, 0xF0D3D6, 0xDED3EA, 0x3A4A34]

# ── Wire format: the companion as an 8-char shortcode ──────────────────────────
#
#   H1A003C1   =  head 1, accessories bril+snor, backdrop 1
#   ^ ^^^^ ^
#   | |  | +-- C: 1-based index into BGS
#   | |  +---- A: 12-bit accessory mask, three HEX digits
#   +-+------- H: 1-based index into HEADS
#
# The server stores this in players.profile_pic. It exists because the badge's
# own head/accs/bg lists don't survive a wipe — the shortcode is what the
# restore flow gets back, and the only thing that makes a recovered profile
# look like the player's own companion instead of a default fox.
#
# Indices are 1-based so a 0 can never be mistaken for "unset". The mask is hex
# rather than decimal because 11 accessories need more than the 10 bits three
# decimal digits would give; 12 bits leaves exactly one spare slot.
#
# BIT POSITIONS ARE APPEND-ONLY: bit i is _ACCS_WIRE[i], so a new accessory
# goes at the END of ACCS. Inserting one in the middle silently rewrites every
# shortcode already stored on the server.
_ACCS_WIRE = [a["id"] for a in ACCS if a["id"] != "geen"]

_DEFAULT_COMPANION = (HEADS[0]["id"], [], 0)


def encode(head_id, accs, bg):
    """(head id, accessory ids, backdrop index) -> "H1A003C1"."""
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
    return "H%dA%03XC%d" % (h, mask, c)


def decode(code):
    """ "H1A003C1" -> (head id, accessory ids, backdrop index).

    Anything malformed or out of range falls back to the default companion: a
    profile that renders beats an error dialog halfway through a restore, and
    an old badge reading a code from a newer roster is a case we'd rather
    degrade than refuse."""
    try:
        if len(code) != 8 or code[0] != "H" or code[2] != "A" or code[6] != "C":
            return _DEFAULT_COMPANION
        h = int(code[1])
        mask = int(code[3:6], 16)
        c = int(code[7])
    except (TypeError, ValueError):
        return _DEFAULT_COMPANION
    head = HEADS[h - 1]["id"] if 1 <= h <= len(HEADS) else HEADS[0]["id"]
    accs = [aid for i, aid in enumerate(_ACCS_WIRE) if mask & (1 << i)]
    return head, accs, (c - 1 if 1 <= c <= len(BGS) else 0)


# reference face the accessories were drawn on
_EYE_REF, _MOUTH_REF = 7, 11


def head_by_id(hid):
    for h in HEADS:
        if h["id"] == hid:
            return h
    return HEADS[0]


def acc_by_id(aid):
    for a in ACCS:
        if a["id"] == aid:
            return a
    return None


def head_rows(h):
    return h.get("rows") or art.SH[h["shape"]]


def head_pal(h):
    return art.PALS[h["pal"]]


def is_unlocked(acc, caught_count, has_legendary):
    u = acc.get("unlock", 0)
    if u == "leg":
        return has_legendary
    return caught_count >= u


def crop(rows):
    """Trim a sprite grid to its ink, so an accessory can be shown centred on
    a tile instead of floating in its (mostly empty) 16x16 frame."""
    top, bottom, left, right = 1000, -1, 1000, -1
    for y, row in enumerate(rows):
        for x, ch in enumerate(row):
            if ch != "." and ch != " ":
                top = min(top, y)
                bottom = max(bottom, y)
                left = min(left, x)
                right = max(right, x)
    if bottom < 0:
        return rows
    return [row[left : right + 1] for row in rows[top : bottom + 1]]


def draw(parent, head_id, accs, scale, x=0, y=0):
    """The composed companion: head layer + each accessory layer, anchored.
    Returns the (transparent) wrapper box, 16*scale square."""
    h = head_by_id(head_id)
    px = 16 * scale
    wrap = ui.box(parent, x, y, px, px, None)
    art.draw_sprite(wrap, head_rows(h), head_pal(h), scale)
    for aid in accs:
        a = acc_by_id(aid)
        if a is None or "rows" not in a:
            continue
        anchor = a.get("anchor")
        if anchor == "eye":
            dy = h["eye"] - _EYE_REF
        elif anchor == "mouth":
            dy = h["mouth"] - _MOUTH_REF
        else:
            dy = 0
        spr = art.draw_sprite(wrap, a["rows"], a["pal"], scale)
        spr.set_pos(0, dy * scale)
    return wrap
