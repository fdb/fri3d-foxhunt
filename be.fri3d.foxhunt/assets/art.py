# art.py — placeholder pixel-art creatures, drawn on an LVGL canvas.
#
# 4 reusable 16x16 shapes (fox/owl/deer/bird) recoloured by palette = all 12
# beasts, no image assets. Same canvas+set_px pattern as the built-in
# space_invaders app, extended with per-pixel palette, scaling and silhouette.
# This whole module is the art swap point: drop in real sprites here later and
# every screen picks them up unchanged.

import lvgl as lv

# chars: '.' transparent | k outline | r body | d dark-body | l light-body
#        w white | e eye | n nose | b beak/horn(gold)
SH = {
    "fox": [
        "................",
        "..k..........k..",
        ".krk........krk.",
        ".krrk......krrk.",
        ".krrrkk..kkrrrk.",
        "..krrrrkkrrrrk..",
        "..krrrrrrrrrrk..",
        "..krwwrrrrwwrk..",
        "..krweerwweerk..",
        "..krrrrrrrrrrk..",
        "..krrlllllllrk..",
        "..kdrllnnllrdk..",
        "..kdrlllllllrk..",
        "...kddrrrrddk...",
        "....kkddddkk....",
        "......kkkk......",
    ],
    "owl": [
        "................",
        "...k........k...",
        "..krk......krk..",
        "..krrkkkkkkrrk..",
        ".krrrrrrrrrrrrk.",
        ".krwwwrrrrwwwrk.",
        ".krweewrrweewrk.",
        ".krwwwrbbrwwwrk.",
        ".krrrrrbbrrrrrk.",
        ".krrlllllllllrk.",
        ".krrlrlrlrlrlrk.",
        "..krrlllllllrk..",
        "..kdrrrrrrrrdk..",
        "...kddbbbbddk...",
        "....kkbbbbkk....",
        "......kkkk......",
    ],
    "deer": [
        "..b..b...b..b...",
        "..b..bb.bb..b...",
        "..bb..bbb..bb...",
        "...bb..b..bb....",
        ".....krrrk......",
        "....krrrrrk.....",
        "....krwrwrk.....",
        "....kreererk....",
        "....krrnnrrk....",
        "...krrrrrrrrk...",
        "..krrlrrrrlrrk..",
        "..krrlrrrrlrrk..",
        "..krrrrrrrrrrk..",
        "...kdrrrrrrdk...",
        "...kdk....kdk...",
        "...kk......kk...",
    ],
    "bird": [
        "......bbb.......",
        ".....bkrkb......",
        "......krk.......",
        ".....krrrk......",
        "....krwrwrk.....",
        "....kreererk....",
        "...bbkrrnrrk....",
        "..b..krrrrrk....",
        ".b..krrrrrrrk...",
        "....krrllrrrk...",
        "....krllllrrk...",
        "....krrllrrdk...",
        "....kdrrrrdk....",
        ".....kdrrdk.b...",
        "...b..kkdk.bb...",
        "...bb..kk..b....",
    ],
}

HEART = [
    ".kk...kk.",
    "krrkkkrrk",
    "krrrrrrrk",
    "krrrrrrrk",
    ".krrrrrk.",
    "..krrrk..",
    "...krk...",
    "....k....",
]

# ── UI icons (action bar + foods), ported from the design ───────────────────
# Mostly 8x8; each has its own palette, and chars not in the palette are
# skipped (transparent). draw_sprite() reads the grid off the rows, so an icon
# is free to be a different size — "backspace" is 17x11.
ICONS = {
    "food": {
        "rows": [
            "...gg...",
            "..gkk...",
            ".kkrrk..",
            "krrrrrk.",
            "krrwrrk.",
            "krrrrrk.",
            ".krrrk..",
            "..kkk...",
        ],
        "pal": {"g": 0x5A9A3C, "r": 0xD6483A, "w": 0xF6CF93, "k": 0x34271A},
    },
    "paw": {
        "rows": [
            "p.p.p.p.",
            "p.p.p.p.",
            "........",
            ".ppppp..",
            "ppppppp.",
            "ppppppp.",
            ".ppppp..",
            "........",
        ],
        "pal": {"p": 0x8A5A2E},
    },
    "ball": {
        "rows": [
            "..kkkk..",
            ".kwwrrk.",
            "kwwrrrrk",
            "kwrrkkrk",
            "krrkkrrk",
            "krrrrrwk",
            ".krrwwk.",
            "..kkkk..",
        ],
        "pal": {"k": 0x34271A, "r": 0xCF6A3F, "w": 0xF6CF93},
    },
    "book": {
        "rows": [
            "kkkkkkk.",
            "kwwwwwwk",
            "kwkwwkwk",
            "kwwwwwwk",
            "kwkwwkwk",
            "kwwwwwwk",
            "kwwwwwwk",
            "kkkkkkk.",
        ],
        "pal": {"k": 0x34271A, "w": 0xEFE0BB},
    },
    "nut": {
        "rows": [
            "..kkk...",
            ".kbbbk..",
            "kbbbbbk.",
            "kbdddbk.",
            "kbddddbk",
            ".kdddbk.",
            "..kddk..",
            "...kk...",
        ],
        "pal": {"k": 0x34271A, "b": 0xCAA05A, "d": 0x8A5F2C},
    },
    # The classic backspace key: a tag pointing left, with the X knocked out of
    # it. Red, because it is the one key that destroys what you typed. 17x11,
    # because the X needs 2px-thick arms — 1px diagonals never touch, so they
    # read as loose dots instead of a cross.
    "backspace": {
        "rows": [
            ".....kkkkkkkkkkkk",
            "....krrrrrrrrrrrk",
            "...krrrwwrrrrwwrk",
            "..krrrrrwwrrwwrrk",
            ".krrrrrrrwwwwrrrk",
            "krrrrrrrrrwwrrrrk",
            ".krrrrrrrwwwwrrrk",
            "..krrrrrwwrrwwrrk",
            "...krrrwwrrrrwwrk",
            "....krrrrrrrrrrrk",
            ".....kkkkkkkkkkkk",
        ],
        "pal": {"k": 0x34271A, "r": 0xD6483A, "w": 0xFFF7E6},
    },
    "acorn": {
        "rows": [
            ".kkkkk..",
            "kbkbkbk.",
            "kbbbbbk.",
            ".kdddk..",
            ".kdddk..",
            "..kdk...",
            "..kdk...",
            "...k....",
        ],
        "pal": {"k": 0x34271A, "b": 0x9A7541, "d": 0xC89A5A},
    },
}


def icon(parent, name, scale=2):
    """Render an 8x8 UI icon onto a transparent canvas. Returns the canvas."""
    ic = ICONS[name]
    return draw_sprite(parent, ic["rows"], ic["pal"], scale)


_BASE = {"k": 0x34271A, "w": 0xFFF7E6, "e": 0x241A12, "n": 0xCF6A4E, "b": 0xF0C64A}


def _pal(r, d, l):
    p = dict(_BASE)
    p["r"], p["d"], p["l"] = r, d, l
    return p


PALS = {
    "orange": _pal(0xE58A3A, 0xB15F24, 0xF6CF93),
    "grey": _pal(0x9A958C, 0x6D6860, 0xD8D3C7),
    "brown": _pal(0xA9743F, 0x7C4F28, 0xD8AD77),
    "cream": _pal(0xEAD9B0, 0xBDA273, 0xF8EECB),
    "green": _pal(0x6AA24A, 0x467030, 0xA6CF7E),
    "tan": _pal(0xCDA268, 0x9A7541, 0xECD3A0),
    "bluegrey": _pal(0x7F93A6, 0x566677, 0xBCC9D6),
    "gold": _pal(0xECC24A, 0xB1841F, 0xF8E6A0),
}

_SIL = 0x2B241D  # silhouette colour for dormant / scanning


def draw_sprite(parent, rows, palette, scale, tint=None):
    """Draw a pixel sprite onto a fresh transparent canvas, each source pixel
    as a scale x scale block. Returns the lv.canvas widget.

    tint (a colour) flattens every opaque pixel to that one colour, keeping only
    the outline — a dark silhouette while hunting, white while typing the code."""
    w = len(rows[0]) * scale
    h = len(rows) * scale
    canvas = lv.canvas(parent)
    canvas.set_size(w, h)
    buf = bytearray(w * h * 4)  # ARGB8888 -> real alpha
    canvas.set_buffer(buf, w, h, lv.COLOR_FORMAT.ARGB8888)
    canvas.set_style_bg_opa(lv.OPA.TRANSP, 0)
    canvas.fill_bg(lv.color_hex(0x000000), lv.OPA.TRANSP)
    cover = lv.OPA.COVER
    for y, row in enumerate(rows):
        by = y * scale
        for x in range(len(row)):
            ch = row[x]
            if ch == "." or ch == " ":
                continue
            col = tint if tint is not None else palette.get(ch)
            if col is None:
                continue
            color = lv.color_hex(col)
            bx = x * scale
            for dy in range(scale):
                yy = by + dy
                for dx in range(scale):
                    canvas.set_px(bx + dx, yy, color, cover)
    # NB: lv.canvas.set_buffer() roots the buffer C-side (same as the built-in
    # space_invaders app), so we don't keep a Python ref — and native widgets
    # have no __dict__ to hang one on anyway.
    return canvas


# ── Creature renderer: real PNG art when present, procedural otherwise ──────
# Creature PNGs are authored at 16x16 RGBA (same grid as the shapes) and live
# in assets/sprites/ (NOT assets/creatures/ — that would shadow creatures.py on
# import). A creature opts in via its "img" field (see creatures.py).
_CREATURE_DIR = "M:apps/be.fri3d.foxhunt/assets/sprites/"
_IMG_SRC = 16


def _bare(o):
    o.set_style_pad_all(0, 0)
    o.set_style_border_width(0, 0)
    o.set_style_radius(0, 0)
    o.set_style_bg_opa(lv.OPA.TRANSP, 0)
    o.remove_flag(lv.obj.FLAG.SCROLLABLE)
    o.remove_flag(lv.obj.FLAG.CLICKABLE)  # let taps fall through to the cell


def _layer(parent, c, scale, tint=None):
    """One creature image/canvas at (0,0), sized 16*scale, full colour (tint
    None) or flattened to `tint`. Non-clickable so it never steals taps from a
    clickable cell."""
    px = 16 * scale
    if c.get("img"):
        w = lv.image(parent)
        w.set_src(_CREATURE_DIR + c["img"])
        w.set_pos(0, 0)
        w.set_size(px, px)
        w.set_inner_align(lv.image.ALIGN.STRETCH)  # scale src(16) to fill px x px
        w.set_antialias(False)  # nearest-neighbour -> crisp
        if tint is not None:
            w.set_style_image_recolor(lv.color_hex(tint), 0)
            w.set_style_image_recolor_opa(lv.OPA.COVER, 0)
    else:
        w = draw_sprite(parent, SH[c["shape"]], PALS[c["pal"]], scale, tint)
        w.set_pos(0, 0)
    w.remove_flag(lv.obj.FLAG.CLICKABLE)
    return w


def creature_panel(parent, c, scale, reveal=1.0, silhouette=False, mask=None):
    """The creature shown full / silhouette / partially revealed (fills
    top-down). Backend-agnostic — PNG art and procedural sprites both come
    through here. Full/silhouette return the bare sprite (no wrapper, so it
    never blocks clicks); only the partial-reveal case needs a clip wrapper.

    `mask` (a colour) fills the revealed part with that flat colour instead of
    the real art: the code screen shows typing progress without spoiling which
    creature it is. The true reveal is the win screen."""
    if silhouette or reveal <= 0.0:
        return _layer(parent, c, scale, _SIL)
    if reveal >= 1.0:
        return _layer(parent, c, scale, mask)
    # partial: silhouette base + revealed part clipped to the top `reveal`
    px = 16 * scale
    wrap = lv.obj(parent)
    _bare(wrap)
    wrap.set_size(px, px)
    _layer(wrap, c, scale, _SIL)
    clip = lv.obj(wrap)
    _bare(clip)
    clip.set_size(px, max(1, int(reveal * px)))
    clip.set_pos(0, 0)
    _layer(clip, c, scale, mask)
    return wrap
