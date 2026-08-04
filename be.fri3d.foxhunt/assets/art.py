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
# is free to be a different size — "backspace" is 13x9.
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
    # it. Red, because it is the one key that destroys what you typed. 13x9 at
    # scale 2 stands as tall as a digit on the neighbouring keys, and the X
    # arms are 2px because 1px diagonals never touch — they read as loose dots
    # instead of a cross, however big you draw them.
    "backspace": {
        "rows": [
            "....kkkkkkkkk",
            "...krrrrrrrrk",
            "..krrwwrrwwrk",
            ".krrrrwwwwrrk",
            "krrrrrrwwrrrk",
            ".krrrrwwwwrrk",
            "..krrwwrrwwrk",
            "...krrrrrrrrk",
            "....kkkkkkkkk",
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
    # ── onboarding icons (registration flow) ────────────────────────────
    # The LoRa antenna: two signal rays over a mast. Gold rays on ink.
    "ant": {
        "rows": [
            "b.....b.",
            ".b...b..",
            "..b.b...",
            "...k....",
            "...k....",
            "..kkk...",
            ".kk.kk..",
            "kk...kk.",
        ],
        "pal": {"k": 0x34271A, "b": 0xC98A2E},
    },
    # Step verdicts for the send-checklist: check / cross / clock.
    "st_ok": {
        "rows": [
            "........",
            "......gg",
            ".....gg.",
            "g...gg..",
            "gg.gg...",
            ".ggg....",
            "..g.....",
            "........",
        ],
        "pal": {"g": 0x4E8A2E},
    },
    "st_bad": {
        "rows": [
            "r......r",
            "rr....rr",
            ".rr..rr.",
            "..rrrr..",
            "..rrrr..",
            ".rr..rr.",
            "rr....rr",
            "r......r",
        ],
        "pal": {"r": 0xC2452F},
    },
    "st_wait": {
        "rows": [
            "..kkkk..",
            ".k....k.",
            "k..kk..k",
            "k..kk..k",
            "k..kkk.k",
            "k......k",
            ".k....k.",
            "..kkkk..",
        ],
        "pal": {"k": 0x8A7D5E},
    },
    # Padlock on a not-yet-unlocked accessory tile.
    "lock": {
        "rows": [
            "..kkkk..",
            ".k....k.",
            ".k....k.",
            "kkkkkkkk",
            "kkkwwkkk",
            "kkkwwkkk",
            "kkkkkkkk",
            "........",
        ],
        "pal": {"k": 0x8A7D5E, "w": 0xEFE7D0},
    },
    # 5x5 gold sparkle for the success splash.
    "spark": {
        "rows": ["..b..", "..b..", "bbkbb", "..b..", "..b.."],
        "pal": {"k": 0xFFF7E6, "b": 0xF0C64A},
    },
    # Settings gear (home header) and the edit pencil (profile page).
    # The gear is 16x16: a classic 8-tooth outline-and-grey gear reads as a
    # gear at 16px where the old 8x8 ring of dots read as a sprocket smudge.
    "gear": {
        "rows": [
            "......kkkk......",
            "......kggk......",
            "..kkk.kggk.kkk..",
            "..kggkggggkggk..",
            "..kggggkkggggk..",
            "...kggk..kggk...",
            "kkkggk....kggkkk",
            "kgggk......kgggk",
            "kgggk......kgggk",
            "kkkggk....kggkkk",
            "...kggk..kggk...",
            "..kggggkkggggk..",
            "..kggkggggkggk..",
            "..kkk.kggk.kkk..",
            "......kggk......",
            "......kkkk......",
        ],
        "pal": {"k": 0x34271A, "g": 0xD8D3C7},
    },
    "pencil": {
        "rows": [
            "......kk",
            ".....kbk",
            "....kbbk",
            "...kbbk.",
            "..kbbk..",
            ".kwbk...",
            "kwwk....",
            "kkk.....",
        ],
        "pal": {"k": 0x34271A, "b": 0xD9A441, "w": 0xEFE0BB},
    },
    # Checkmark on the picked colour swatch (dark, plus a light variant for
    # the one dark swatch).
    "check": {
        "rows": [
            "........kk",
            ".......kk.",
            "......kk..",
            "k....kk...",
            "kk..kk....",
            ".kkkkk....",
            "..kkk.....",
            "...k......",
        ],
        "pal": {"k": 0x2B3A52},
    },
    "check_light": {
        "rows": [
            "........kk",
            ".......kk.",
            "......kk..",
            "k....kk...",
            "kk..kk....",
            ".kkkkk....",
            "..kkk.....",
            "...k......",
        ],
        "pal": {"k": 0xF2EAD6},
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

# ── Tones: how a creature is flattened when it must not be recognisable ─────
# A tone is (fill, outline); outline None means the whole shape is one flat
# colour. Which tone reads depends entirely on what it sits on, hence three.
SIL = (0x2B241D, None)  # dark silhouette on a LIGHT card (grid, hunt scan)
GHOST = (0x41342A, 0x4E4136)  # barely-there shape on the DARK code panel: a
#                               hair lighter than the ground, with an outline
#                               a hair lighter again, so you can tell there is
#                               something there without telling WHAT.
MASK = (0xFFF7E6, None)  # flat white: typing progress, still not the art


def draw_sprite(parent, rows, palette, scale, tint=None):
    """Draw a pixel sprite onto a fresh transparent canvas, each source pixel
    as a scale x scale block. Returns the lv.canvas widget.

    tint is a tone (see above) that flattens every opaque pixel: outline pixels
    ('k') take the tone's outline colour, everything else its fill. None draws
    the sprite in its real palette."""
    fill, edge = tint if tint else (None, None)
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
            if fill is None:
                col = palette.get(ch)
            else:
                col = edge if (edge is not None and ch == "k") else fill
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


# ── Baked artwork: one atlas for every 16x16 sprite ─────────────────────────
# scripts/bake_sprites.sh packs artwork/**/16px PNGs into assets/sprites.bin
# (raw BGRA frames, 1 KB each) + the generated atlas.py index — one LittleFS
# file instead of forty. A sprite is named by its artwork-relative path
# ("animals/vos.png"); a sheet (width N*16) is N consecutive frames. Only
# screen-sized art (the title banner) is still a real PNG on disk.
import atlas

# open() path, derived from where this module was imported from, so it holds
# on badge and desktop alike. The title PNG goes through LVGL's own fs layer
# instead, which wants its M: driver letter and its canonical path.
_SPRITE_BIN = __file__.rsplit("/", 1)[0] + "/sprites.bin"
TITLE_SRC = "M:apps/be.fri3d.foxhunt/assets/title-screen/title-screen.png"
_IMG_SRC = 16
_FRAME_BYTES = _IMG_SRC * _IMG_SRC * 4

# (name, frame) -> (dsc, data). The dsc holds a raw pointer INTO data, so the
# bytes must stay referenced as long as the dsc lives — hence caching both.
_dsc_cache = {}


def frames(name):
    """How many animation frames the atlas holds for this sprite (1 = still)."""
    return atlas.SPRITES[name][1]


def sprite_dsc(name, frame=0):
    """One 16x16 atlas frame as an lv.image_dsc_t (seek + 1 KB read, cached).
    No PNG decode: sprites.bin already holds the bytes LVGL blits."""
    key = (name, frame)
    hit = _dsc_cache.get(key)
    if hit:
        return hit[0]
    base, count = atlas.SPRITES[name]
    with open(_SPRITE_BIN, "rb") as f:
        f.seek((base + frame % count) * _FRAME_BYTES)
        data = f.read(_FRAME_BYTES)
    dsc = lv.image_dsc_t(
        {
            "header": {
                "cf": lv.COLOR_FORMAT.ARGB8888,
                "w": _IMG_SRC,
                "h": _IMG_SRC,
                "stride": _IMG_SRC * 4,
            },
            "data_size": _FRAME_BYTES,
            "data": data,
        }
    )
    _dsc_cache[key] = (dsc, data)
    return dsc


def sprite_img(parent, name, scale, x=0, y=0, frame=0):
    """A baked 16x16 sprite blown up to 16*scale, nearest-neighbour, at (x, y).
    The image counterpart of draw_sprite() — same grid, same scale factor, so
    a caller can swap art backends without moving anything else."""
    px = _IMG_SRC * scale
    w = lv.image(parent)
    w.set_src(sprite_dsc(name, frame))
    w.set_pos(x, y)
    w.set_size(px, px)
    w.set_inner_align(lv.image.ALIGN.STRETCH)  # scale src(16) to fill px x px
    w.set_antialias(False)  # nearest-neighbour -> crisp
    w.remove_flag(lv.obj.FLAG.CLICKABLE)  # let taps fall through to the cell
    return w


_ANIM_FRAME_MS = 180  # sprite-sheet playback: ~5.5 fps reads as pixel art


def animate_sprite(img, name, ms=_ANIM_FRAME_MS):
    """Cycle a sprite_img through its sheet frames, forever.

    An lv.anim_t rather than an lv.timer for the same reason as
    companion._twinkle: LVGL kills an animation when its var is deleted, so
    playback dies with the widget and a rebuilt screen never leaks a timer
    poking a dead image. Values run 0..n over n*ms so each frame gets one
    slot; %n folds the endpoint back onto frame 0."""
    n = frames(name)
    if n < 2:
        return
    a = lv.anim_t()
    a.init()
    a.set_var(img)
    a.set_values(0, n)
    a.set_duration(n * ms)
    a.set_repeat_count(lv.ANIM_REPEAT_INFINITE)
    a.set_custom_exec_cb(lambda _a, v: img.set_src(sprite_dsc(name, v % n)))
    a.start()


def picture(parent, src, x=0, y=0):
    """A baked PNG drawn at its authored size — nearest-neighbour, so the
    pixels stay pixels. For art that is already screen-sized (the title
    banner); creature art goes through creature_panel() instead."""
    w = lv.image(parent)
    w.set_src(src)
    w.set_pos(x, y)
    w.set_antialias(False)
    return w


def _bare(o):
    o.set_style_pad_all(0, 0)
    o.set_style_border_width(0, 0)
    o.set_style_radius(0, 0)
    o.set_style_bg_opa(lv.OPA.TRANSP, 0)
    o.remove_flag(lv.obj.FLAG.SCROLLABLE)
    o.remove_flag(lv.obj.FLAG.CLICKABLE)  # let taps fall through to the cell


def _layer(parent, c, scale, tint=None, animate=False):
    """One creature image/canvas at (0,0), sized 16*scale, full colour (tint
    None) or flattened to the tone `tint`. Non-clickable so it never steals
    taps from a clickable cell.

    Caveat: recolouring an image is all-or-nothing, so PNG art takes the tone's
    fill and skips its outline. That is a difference you can only see by
    hunting for it, and the alternative — recolouring at partial opacity —
    would leak the real colours, which is the whole thing we are hiding."""
    if c.get("img"):
        name = "animals/" + c["img"]
        w = sprite_img(parent, name, scale)
        if tint is not None:
            w.set_style_image_recolor(lv.color_hex(tint[0]), 0)
            w.set_style_image_recolor_opa(lv.OPA.COVER, 0)
        elif animate and c.get("anim"):
            animate_sprite(w, name)
    else:
        w = draw_sprite(parent, SH[c["shape"]], PALS[c["pal"]], scale, tint)
        w.set_pos(0, 0)
        w.remove_flag(lv.obj.FLAG.CLICKABLE)
    return w


def creature_panel(
    parent, c, scale, reveal=1.0, silhouette=False, mask=None, veil=SIL, animate=False
):
    """The creature shown full / hidden / partially revealed (fills top-down).
    Backend-agnostic — PNG art and procedural sprites both come through here.
    Full/hidden return the bare sprite (no wrapper, so it never blocks clicks);
    only the partial-reveal case needs a clip wrapper.

    `veil` is the tone the not-yet-revealed part is drawn in, `mask` the tone
    the revealed part takes instead of the real art (None = the real art, i.e.
    an honest reveal). The code screen sets both, so it can show progress
    without ever spoiling which creature it is — the true reveal is the win
    screen.

    `animate` plays a sprite sheet's frames, for creatures flagged "anim" —
    only ever on the honest full reveal (the payoff screens and the beast
    page); silhouettes and veils hold frame 0 so a mystery stays still."""
    if silhouette or reveal <= 0.0:
        return _layer(parent, c, scale, veil)
    if reveal >= 1.0:
        return _layer(parent, c, scale, mask, animate=(animate and mask is None))
    # partial: veiled base + revealed part clipped to the top `reveal`
    px = 16 * scale
    wrap = lv.obj(parent)
    _bare(wrap)
    wrap.set_size(px, px)
    _layer(wrap, c, scale, veil)
    clip = lv.obj(wrap)
    _bare(clip)
    clip.set_size(px, max(1, int(reveal * px)))
    clip.set_pos(0, 0)
    _layer(clip, c, scale, mask)
    return wrap
