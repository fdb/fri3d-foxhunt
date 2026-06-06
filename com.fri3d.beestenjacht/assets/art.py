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
        "................", "..k..........k..", ".krk........krk.", ".krrk......krrk.",
        ".krrrkk..kkrrrk.", "..krrrrkkrrrrk..", "..krrrrrrrrrrk..", "..krwwrrrrwwrk..",
        "..krweerwweerk..", "..krrrrrrrrrrk..", "..krrlllllllrk..", "..kdrllnnllrdk..",
        "..kdrlllllllrk..", "...kddrrrrddk...", "....kkddddkk....", "......kkkk......",
    ],
    "owl": [
        "................", "...k........k...", "..krk......krk..", "..krrkkkkkkrrk..",
        ".krrrrrrrrrrrrk.", ".krwwwrrrrwwwrk.", ".krweewrrweewrk.", ".krwwwrbbrwwwrk.",
        ".krrrrrbbrrrrrk.", ".krrlllllllllrk.", ".krrlrlrlrlrlrk.", "..krrlllllllrk..",
        "..kdrrrrrrrrdk..", "...kddbbbbddk...", "....kkbbbbkk....", "......kkkk......",
    ],
    "deer": [
        "..b..b...b..b...", "..b..bb.bb..b...", "..bb..bbb..bb...", "...bb..b..bb....",
        ".....krrrk......", "....krrrrrk.....", "....krwrwrk.....", "....kreererk....",
        "....krrnnrrk....", "...krrrrrrrrk...", "..krrlrrrrlrrk..", "..krrlrrrrlrrk..",
        "..krrrrrrrrrrk..", "...kdrrrrrrdk...", "...kdk....kdk...", "...kk......kk...",
    ],
    "bird": [
        "......bbb.......", ".....bkrkb......", "......krk.......", ".....krrrk......",
        "....krwrwrk.....", "....kreererk....", "...bbkrrnrrk....", "..b..krrrrrk....",
        ".b..krrrrrrrk...", "....krrllrrrk...", "....krllllrrk...", "....krrllrrdk...",
        "....kdrrrrdk....", ".....kdrrdk.b...", "...b..kkdk.bb...", "...bb..kk..b....",
    ],
}

HEART = [
    ".kk...kk.", "krrkkkrrk", "krrrrrrrk", "krrrrrrrk",
    ".krrrrrk.", "..krrrk..", "...krk...", "....k....",
]

_BASE = {"k": 0x34271A, "w": 0xFFF7E6, "e": 0x241A12, "n": 0xCF6A4E, "b": 0xF0C64A}


def _pal(r, d, l):
    p = dict(_BASE)
    p["r"], p["d"], p["l"] = r, d, l
    return p


PALS = {
    "orange":   _pal(0xE58A3A, 0xB15F24, 0xF6CF93),
    "grey":     _pal(0x9A958C, 0x6D6860, 0xD8D3C7),
    "brown":    _pal(0xA9743F, 0x7C4F28, 0xD8AD77),
    "cream":    _pal(0xEAD9B0, 0xBDA273, 0xF8EECB),
    "green":    _pal(0x6AA24A, 0x467030, 0xA6CF7E),
    "tan":      _pal(0xCDA268, 0x9A7541, 0xECD3A0),
    "bluegrey": _pal(0x7F93A6, 0x566677, 0xBCC9D6),
    "gold":     _pal(0xECC24A, 0xB1841F, 0xF8E6A0),
}

_SIL = 0x2B241D   # silhouette colour for dormant / scanning


def draw_sprite(parent, rows, palette, scale, silhouette=False, reveal=1.0):
    """Draw a pixel sprite onto a fresh transparent canvas, each source pixel
    as a scale x scale block. Returns the lv.canvas widget.

    reveal (0..1) colours the top fraction of rows and leaves the rest as
    silhouette — the creature "fills in" as the player types the code."""
    w = len(rows[0]) * scale
    h = len(rows) * scale
    cutoff = reveal * len(rows)                       # rows above this are colour
    canvas = lv.canvas(parent)
    canvas.set_size(w, h)
    buf = bytearray(w * h * 4)                       # ARGB8888 -> real alpha
    canvas.set_buffer(buf, w, h, lv.COLOR_FORMAT.ARGB8888)
    canvas.set_style_bg_opa(lv.OPA.TRANSP, 0)
    canvas.fill_bg(lv.color_hex(0x000000), lv.OPA.TRANSP)
    cover = lv.OPA.COVER
    for y, row in enumerate(rows):
        by = y * scale
        row_sil = silhouette or (y >= cutoff)
        for x in range(len(row)):
            ch = row[x]
            if ch == "." or ch == " ":
                continue
            col = _SIL if row_sil else palette.get(ch)
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
_CREATURE_DIR = "M:apps/com.fri3d.beestenjacht/assets/sprites/"
_IMG_SRC = 16


def _bare(o):
    o.set_style_pad_all(0, 0)
    o.set_style_border_width(0, 0)
    o.set_style_radius(0, 0)
    o.set_style_bg_opa(lv.OPA.TRANSP, 0)
    o.remove_flag(lv.obj.FLAG.SCROLLABLE)


def _layer(parent, c, scale, silhouette):
    """One creature image/canvas at (0,0), nominal size 16*scale, full colour
    or silhouette."""
    if c.get("img"):
        img = lv.image(parent)
        img.set_src(_CREATURE_DIR + c["img"])
        img.set_pos(0, 0)
        img.set_pivot(0, 0)                 # scale from top-left so it fills (0,0)->(px,px)
        img.set_antialias(False)            # crisp pixels
        if scale != 1:
            img.set_scale(256 * scale)      # src is 16px -> 16*scale px
        if silhouette:
            img.set_style_image_recolor(lv.color_hex(_SIL), 0)
            img.set_style_image_recolor_opa(lv.OPA.COVER, 0)
        return img
    cv = draw_sprite(parent, SH[c["shape"]], PALS[c["pal"]], scale, silhouette)
    cv.set_pos(0, 0)
    return cv


def creature_panel(parent, c, scale, reveal=1.0, silhouette=False):
    """A 16*scale square wrapper showing the creature full / silhouette /
    partially revealed (colour fills top-down). Backend-agnostic: PNG art and
    procedural sprites both go through here, so every screen behaves the same."""
    px = 16 * scale
    wrap = lv.obj(parent)
    _bare(wrap)
    wrap.set_size(px, px)
    if silhouette or reveal <= 0.0:
        _layer(wrap, c, scale, True)
    elif reveal >= 1.0:
        _layer(wrap, c, scale, False)
    else:
        # silhouette base + colour clipped to the top `reveal` fraction
        _layer(wrap, c, scale, True)
        clip = lv.obj(wrap)
        _bare(clip)
        clip.set_size(px, max(1, int(reveal * px)))
        clip.set_pos(0, 0)
        _layer(clip, c, scale, False)
    return wrap
