# art.py — creature sprites (baked atlas) + hand-drawn UI icons on canvas.
#
# Creature art comes from the baked sprite atlas (see below); the small UI
# icons and hearts are pixel grids drawn with the same canvas+set_px pattern
# as the built-in space_invaders app, with per-pixel palette and scaling.

import lvgl as lv

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
    # Pixels go straight into the ARGB8888 buffer (memory order B,G,R,A —
    # same as the atlas frames): one scaled line built per source row, then
    # block-copied per scale row. set_px would cost a Python->C call per
    # destination pixel — the 16px gear at scale 2 alone is ~1000 of them.
    buf = bytearray(w * h * 4)  # zeroed = fully transparent
    rowbytes = w * 4
    for y, row in enumerate(rows):
        line = bytearray(rowbytes)
        opaque = False
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
            opaque = True
            px = bytes(((col) & 0xFF, (col >> 8) & 0xFF, (col >> 16) & 0xFF, 0xFF))
            o = x * scale * 4
            line[o : o + 4 * scale] = px * scale
        if opaque:
            base = y * scale * rowbytes
            for dy in range(scale):
                o = base + dy * rowbytes
                buf[o : o + rowbytes] = line
    canvas.set_buffer(buf, w, h, lv.COLOR_FORMAT.ARGB8888)
    canvas.set_style_bg_opa(lv.OPA.TRANSP, 0)
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

try:
    from art_fast import upscale as _upscale_fast  # viper, badge only
except Exception:  # desktop build has no native emitter
    _upscale_fast = None

# open() path, derived from where this module was imported from, so it holds
# on badge and desktop alike. The title PNG goes through LVGL's own fs layer
# instead, which wants its M: driver letter and its canonical path.
_SPRITE_BIN = __file__.rsplit("/", 1)[0] + "/sprites.bin"
TITLE_SRC = "M:apps/be.fri3d.foxhunt/assets/title-screen/title-screen.png"
_IMG_SRC = 16
_FRAME_BYTES = _IMG_SRC * _IMG_SRC * 4

# (name, frame) -> the raw 1 KB atlas frame. Bounded by the roster; saves the
# file seek on re-reads and feeds every scaled copy below.
_frame_cache = {}

# Scaled pixel buffers live exactly as long as the widget that shows them: an
# lv.image_dsc_t holds a raw pointer INTO its data bytes, so the bytes must
# stay referenced while the widget draws — but at (16*scale)^2 * 4 they are
# too big to cache forever (one 128px animation is 64 KB a frame). Entries
# are keyed by a counter and dropped by the widget's DELETE event.
_live = {}
_live_n = 0


def frames(name):
    """How many animation frames the atlas holds for this sprite (1 = still)."""
    return atlas.SPRITES[name][1]


def _frame_bytes(name, frame):
    key = (name, frame)
    data = _frame_cache.get(key)
    if data is None:
        base, count = atlas.SPRITES[name]
        with open(_SPRITE_BIN, "rb") as f:
            f.seek((base + frame % count) * _FRAME_BYTES)
            data = f.read(_FRAME_BYTES)
        _frame_cache[key] = data
    return data


def _upscale(src, scale):
    """16x16 BGRA bytes blown up by integer pixel replication: every source
    pixel becomes an exact scale x scale block."""
    if _upscale_fast:
        return _upscale_fast(src, scale)
    srow = _IMG_SRC * 4
    drow = srow * scale
    out = bytearray(len(src) * scale * scale)
    for y in range(_IMG_SRC):
        o = y * srow
        row = b"".join(src[o + 4 * x : o + 4 * x + 4] * scale for x in range(_IMG_SRC))
        d = y * scale * drow
        for _ in range(scale):
            out[d : d + drow] = row
            d += drow
    return out


def _sprite_dsc(name, frame, scale):
    """One atlas frame as an lv.image_dsc_t, pre-scaled to 16*scale square.
    Returns (dsc, data); the caller must keep data referenced (see _keep).
    No PNG decode: sprites.bin already holds the bytes LVGL blits."""
    src = _frame_bytes(name, frame)
    data = src if scale == 1 else _upscale(src, scale)
    px = _IMG_SRC * scale
    dsc = lv.image_dsc_t(
        {
            "header": {
                "cf": lv.COLOR_FORMAT.ARGB8888,
                "w": px,
                "h": px,
                "stride": px * 4,
            },
            "data_size": px * px * 4,
            "data": data,
        }
    )
    return dsc, data


def _keep(w, refs):
    """Anchor `refs` until widget `w` is deleted (its lv DELETE event)."""
    global _live_n
    _live_n += 1
    k = _live_n
    _live[k] = refs
    w.add_event_cb(lambda e: _live.pop(k, None), lv.EVENT.DELETE, None)


def sprite_img(parent, name, scale, x=0, y=0, frame=0):
    """A baked 16x16 sprite blown up to 16*scale at (x, y) — scaled HERE by
    pixel replication, never by LVGL. LVGL's draw-time transform steps the
    source edge-to-edge in (dest_w - 1) increments, which renders half-width
    edge pixels and the odd double-width column even at exact integer factors;
    a buffer that already matches the widget size never enters that path.
    The image counterpart of draw_sprite() — same grid, same scale factor, so
    a caller can swap art backends without moving anything else."""
    dsc, data = _sprite_dsc(name, frame, scale)
    px = _IMG_SRC * scale
    w = lv.image(parent)
    w.set_src(dsc)
    w.set_pos(x, y)
    w.set_size(px, px)
    w.set_antialias(False)
    w.remove_flag(lv.obj.FLAG.CLICKABLE)  # let taps fall through to the cell
    _keep(w, (dsc, data))
    return w


_ANIM_FRAME_MS = 180  # sprite-sheet playback: ~5.5 fps reads as pixel art


def animate_sprite(img, name, scale, ms=_ANIM_FRAME_MS):
    """Cycle a sprite_img through its sheet frames, forever. Every frame is
    pre-scaled up front and anchored to the widget, so a tick is one set_src —
    no allocation, no rescale.

    An lv.anim_t rather than an lv.timer for the same reason as
    companion._twinkle: LVGL kills an animation when its var is deleted, so
    playback dies with the widget and a rebuilt screen never leaks a timer
    poking a dead image. Values run 0..n over n*ms so each frame gets one
    slot; %n folds the endpoint back onto frame 0."""
    n = frames(name)
    if n < 2:
        return
    seq = [_sprite_dsc(name, f, scale) for f in range(n)]
    _keep(img, seq)
    a = lv.anim_t()
    a.init()
    a.set_var(img)
    a.set_values(0, n)
    a.set_duration(n * ms)
    a.set_repeat_count(lv.ANIM_REPEAT_INFINITE)
    a.set_custom_exec_cb(lambda _a, v: img.set_src(seq[v % n][0]))
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

    Caveat: recolouring an image is all-or-nothing, so a tinted sprite takes
    the tone's fill and skips its outline. The alternative — recolouring at
    partial opacity — would leak the real colours, which is the whole thing
    we are hiding."""
    name = "animals/" + c["img"]
    w = sprite_img(parent, name, scale)
    if tint is not None:
        w.set_style_image_recolor(lv.color_hex(tint[0]), 0)
        w.set_style_image_recolor_opa(lv.OPA.COVER, 0)
    elif animate and c.get("anim"):
        animate_sprite(w, name, scale)
    return w


def creature_panel(
    parent, c, scale, reveal=1.0, silhouette=False, mask=None, veil=SIL, animate=False
):
    """The creature shown full / hidden / partially revealed (fills top-down).
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
