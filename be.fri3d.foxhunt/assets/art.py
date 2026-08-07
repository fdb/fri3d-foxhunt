# art.py — creature sprites (baked atlas) + hand-drawn UI icons on canvas.
#
# Creature art comes from the baked sprite atlas (see below); the small UI
# icons and hearts are pixel grids drawn with the same canvas+set_px pattern
# as the built-in space_invaders app, with per-pixel palette and scaling.

import lvgl as lv

# The beste-vriend star: gold 'g' at the call site (ui.GOLD), like HEART's
# palette-at-call-site convention below.
STAR = [
    "....g....",
    "...ggg...",
    "ggggggggg",
    ".ggggggg.",
    "..ggggg..",
    ".ggg.ggg.",
    "gg.....gg",
]
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

# The ring: the ordinary thing the mini-games drop. A HOLLOW silhouette is the
# one shape none of the three hapjes can imitate, so a rare hapje falling among
# rings reads as an event even at full speed — which is the whole point of
# replacing the hapje rain with something duller.
# One grid, three palettes (like HEART, the palette IS the variation). The
# tuple is ordered brons, zilver, goud — cheapest first, so the index doubles
# as what the ring is worth.
RING = [
    "..kkkk..",
    ".kwwcck.",
    "kwc..cck",
    "kc....ck",
    "kc....ck",
    "kcc..cck",
    ".kcccck.",
    "..kkkk..",
]
RING_PALS = (
    {"k": 0x5A3316, "c": 0xC1783A, "w": 0xE8A96A},
    {"k": 0x4A5058, "c": 0xB8BFC6, "w": 0xEFF3F7},
    {"k": 0x6B4A12, "c": 0xE8B84B, "w": 0xFFF0B0},
)

# ── Scenery: the beestenschool backdrops ────────────────────────────────────
# Bare row grids like HEART, not ICONS entries, because here the palette IS the
# depth cue: the same cloud drawn pale and small is far away, drawn bright and
# big it is close, and one tree grid in two greens makes a treeline read as two
# rows. An entry in ICONS would freeze that palette to one distance.
CLOUD = [
    "....wwww..ww..",
    "..wwwwwwwwwww.",
    ".wwwwwwwwwwwww",
    "wwwwwwwwwwwwww",
    "wwwwwwwwwwwwww",
    ".ssssssssssss.",
]
PUFF = [
    "..www....",
    ".wwwwwww.",
    "wwwwwwwww",
    ".sssssss.",
]
TREE = [
    "...ccccc...",
    "..ccccccc..",
    ".ccccccccc.",
    "ccccccccccc",
    "ccccccccccc",
    ".ccccccccc.",
    "..ccccccc..",
    "...ccccc...",
    "....ttt....",
    "....ttt....",
    "....ttt....",
]
PINE = [
    "....c....",
    "...ccc...",
    "..ccccc..",
    "...ccc...",
    "..ccccc..",
    ".ccccccc.",
    "..ccccc..",
    ".ccccccc.",
    "ccccccccc",
    "....t....",
    "....t....",
]
# A camp tent — Fri3d is a field, not a skyline. Lit side 'a', shaded 'b', and
# the gap that widens over the last three rows is the door flap.
TENT = [
    "......aa.....",
    ".....aabb....",
    "....aaabbb...",
    "...aaaabbbb..",
    "..aaaaabbbbb.",
    ".aaaaa.bbbbb.",
    "aaaaa...bbbbb",
    "aaaaa...bbbbb",
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
    # ── verzamelaar-track icons (verzamelen.jsx / plukken.jsx) ──────────
    # Two maatjes shake hands: the snuffel. 16x16, terra + green — one hand
    # per player, the same pair of colours the two home cards wear.
    "snuf": {
        "rows": [
            "................",
            "..aa........bb..",
            ".aaaa......bbbb.",
            ".aaaa......bbbb.",
            "..aa........bb..",
            "................",
            ".aaaa......bbbb.",
            "aaaaaa....bbbbbb",
            "aaaaaa....bbbbbb",
            "aa.aaa....bbb.bb",
            "aa..aaa..bbb..bb",
            "aa...aaabbb...bb",
            "aa....aabb....bb",
            "aa....aabb....bb",
            "................",
            "................",
        ],
        "pal": {"a": 0xCF6A3F, "b": 0x5A9A3C},
    },
    # A hand plucks a berry off the branch. 16x16.
    "pluk": {
        "rows": [
            "..gg.......gg...",
            "bbbbbbbbbbbbbbbb",
            "..gg...b...gg...",
            ".......b........",
            "......rrrr......",
            ".....rrrrrr.....",
            ".....rrrrrr.....",
            "......rrrr......",
            "........h.......",
            "..h....hh.......",
            "..hh..hh........",
            "...hhhhh........",
            "...hhhhhh.......",
            "....hhhhh.......",
            "....hhhh........",
            "................",
        ],
        "pal": {"b": 0x8A5F2C, "g": 0x5A9A3C, "r": 0xD6483A, "h": 0xC98B4E},
    },
    # A low shrub and loose leaf for the random-visitor scene. The three
    # greens keep it readable at scale 2 on the home popup and scale 4 in the
    # full-screen meeting without introducing bitmap files for tiny scenery.
    "bush": {
        "rows": [
            "................",
            ".....llll.......",
            "...llggggll.....",
            "..lggggggggl....",
            ".lggddggggggll..",
            "lgggddggggggggl.",
            "lggggggddggggggl",
            ".lgggggddgggggl.",
            "..llllllllllll..",
            "................",
        ],
        "pal": {"l": 0x3C6B2E, "g": 0x5A9A3C, "d": 0x477D32},
    },
    "leaf": {
        "rows": [
            "......gg",
            "....gggg",
            "..ggggg.",
            ".ggggg..",
            "ggggg...",
            ".ggg....",
            "..g.....",
            ".g......",
        ],
        "pal": {"g": 0x5A9A3C},
    },
    # Rising signal bars (the pluk day-stat strip).
    "sig": {
        "rows": [
            ".......s",
            ".......s",
            ".....s.s",
            ".....s.s",
            "...s.s.s",
            "...s.s.s",
            ".s.s.s.s",
            ".s.s.s.s",
        ],
        "pal": {"s": 0x3C6B2E},
    },
    # A `fri3d-badge` hotspot: rounded antenna dome on a foot. 10x10.
    "hotspot": {
        "rows": [
            "....kk....",
            "...kbbk...",
            "...kbbk...",
            "..kbbbbk..",
            ".kbdddbk..",
            "kbdddddbk.",
            "kbdddddbk.",
            ".kbdddbk..",
            "..kkkkk...",
            "...kkk....",
        ],
        "pal": {"k": 0x34271A, "b": 0x6AA24A, "d": 0x467030},
    },
    # ── beestenschool game tiles ────────────────────────────────────────
    "vlieg": {
        "rows": [
            ".k......",
            ".kwk....",
            ".kwwk.k.",
            "kwwwwkwk",
            "kwwwwwwk",
            ".kwwwwk.",
            "..kwwk..",
            "...kk...",
        ],
        "pal": {"k": 0x34271A, "w": 0xCF6A3F},
    },
    "doolhof": {
        "rows": [
            "kkkkkkkk",
            "k......k",
            "k.kkkk.k",
            "k.k..k.k",
            "k.k.kk.k",
            "k...k..k",
            "kkk.k.kk",
            "......k.",
        ],
        "pal": {"k": 0x34271A},
    },
    "dans": {
        "rows": [
            ".aa..bb.",
            "aaa..bbb",
            ".aa..bb.",
            "..a..b..",
            "..c..d..",
            ".cc..dd.",
            "ccc..ddd",
            ".cc..dd.",
        ],
        "pal": {"a": 0xD6483A, "b": 0xE8B23A, "c": 0x5A9A3C, "d": 0x7F93A6},
    },
}

# Design-name aliases: the verzamelaar screens speak the glossary (bes/noot/
# eikel, boek, spoor) while the icon grid keeps its original keys.
ICONS["bes"] = ICONS["food"]
ICONS["noot"] = ICONS["nut"]
ICONS["eikel"] = ICONS["acorn"]
ICONS["boek"] = ICONS["book"]
ICONS["spoor"] = ICONS["paw"]
# The ring as a plain UI icon (the school tile). Goud, because one ring
# standing for all three should be the one worth chasing.
ICONS["ring"] = {"rows": RING, "pal": RING_PALS[2]}


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
    # lv.canvas.set_buffer() does NOT root the buffer: the binding passes the
    # raw pointer through and LVGL stores it without copying, so a local
    # bytearray is garbage the moment this returns — the canvas then blits
    # whatever the GC reuses the block for. Conservative stack scanning keeps
    # it alive just long enough to survive casual testing, which is how the
    # old "roots it C-side" claim went unnoticed. Anchor it to the widget,
    # exactly like sprite_img anchors its dsc data.
    _keep(canvas, buf)
    return canvas


# ── Baked artwork: one atlas for every 16x16 sprite ─────────────────────────
# scripts/bake_sprites.sh packs artwork/**/16px PNGs into assets/sprites.bin
# (256-byte frames of palette indices, expanded here against atlas.PALETTE)
# + the generated atlas.py index — one LittleFS file instead of forty. A
# sprite is named by its artwork-relative path ("animals/vos.png"); a sheet
# (width N*16) is N consecutive frames. Only screen-sized art (the title
# banner) is still a real PNG on disk.
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
_IDX_BYTES = _IMG_SRC * _IMG_SRC  # on disk: one atlas.PALETTE index per pixel

# (name, frame) -> the frame expanded to 1 KB of BGRA. Bounded by the roster;
# saves the file seek and the palette expansion on re-reads and feeds every
# scaled copy below.
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
            f.seek((base + frame % count) * _IDX_BYTES)
            idx = f.read(_IDX_BYTES)
        out = bytearray(_FRAME_BYTES)
        pal = atlas.PALETTE
        for i in range(_IDX_BYTES):
            c = idx[i] * 4
            o = i * 4
            out[o : o + 4] = pal[c : c + 4]
        data = bytes(out)
        _frame_cache[key] = data
    return data


def _upscale(src, scale):
    """16x16 BGRA bytes blown up by integer pixel replication: every source
    pixel becomes an exact scale x scale block."""
    # The viper twin hardcodes the 16x16 frame size and does not bounds-check,
    # so a short buffer would be read 1024 bytes past its end silently; the
    # pure-Python path merely produces a wrong-sized image. Only hand it
    # exactly what it assumes.
    if _upscale_fast and len(src) == _FRAME_BYTES:
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


def _flip_x(src):
    """Mirror one 16x16 BGRA atlas frame without involving LVGL transforms."""
    row_size = _IMG_SRC * 4
    out = bytearray(len(src))
    for y in range(_IMG_SRC):
        row = y * row_size
        for x in range(_IMG_SRC):
            src_x = row + x * 4
            dst_x = row + (_IMG_SRC - 1 - x) * 4
            out[dst_x : dst_x + 4] = src[src_x : src_x + 4]
    # Keep the same immutable type as an atlas frame. MicroPython does not
    # implement ``bytearray * int``, which _upscale uses to replicate pixels.
    return bytes(out)


def _sprite_dsc(name, frame, scale, flip_x=False):
    """One atlas frame as an lv.image_dsc_t, pre-scaled to 16*scale square.
    Returns (dsc, data); the caller must keep data referenced (see _keep).
    No PNG decode: sprites.bin already holds the bytes LVGL blits."""
    src = _frame_bytes(name, frame)
    if flip_x:
        src = _flip_x(src)
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


def sprite_img(parent, name, scale, x=0, y=0, frame=0, flip_x=False):
    """A baked 16x16 sprite blown up to 16*scale at (x, y) — scaled HERE by
    pixel replication, never by LVGL. LVGL's draw-time transform steps the
    source edge-to-edge in (dest_w - 1) increments, which renders half-width
    edge pixels and the odd double-width column even at exact integer factors;
    a buffer that already matches the widget size never enters that path.
    The image counterpart of draw_sprite() — same grid, same scale factor, so
    a caller can swap art backends without moving anything else."""
    dsc, data = _sprite_dsc(name, frame, scale, flip_x)
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


def animate_sprite(img, name, scale, ms=_ANIM_FRAME_MS, flip_x=False):
    """Cycle a sprite_img through its sheet frames, forever. Frames are scaled
    LAZILY, on their first showing, and cached on the widget: eager pre-scaling
    allocated every frame before the screen drew anything — at the legendary
    win screen's scale 8 that was 10 x 64 KB in one burst, a MemoryError risk
    at the game's single biggest payoff moment. Spread over the first cycle,
    the GC gets a turn between frames; after one loop a tick is one set_src.

    An lv.anim_t rather than an lv.timer for the same reason as
    companion._twinkle: LVGL kills an animation when its var is deleted, so
    playback dies with the widget and a rebuilt screen never leaks a timer
    poking a dead image. Values run 0..n over n*ms so each frame gets one
    slot; %n folds the endpoint back onto frame 0."""
    n = frames(name)
    if n < 2:
        return
    cache = {}  # frame index -> (dsc, data); anchored below, filled on demand
    _keep(img, cache)

    def _show(f):
        d = cache.get(f)
        if d is None:
            d = _sprite_dsc(name, f, scale, flip_x)
            cache[f] = d
        img.set_src(d[0])

    a = lv.anim_t()
    a.init()
    a.set_var(img)
    a.set_values(0, n)
    a.set_duration(n * ms)
    a.set_repeat_count(lv.ANIM_REPEAT_INFINITE)
    a.set_custom_exec_cb(lambda _a, v: _show(v % n))
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


def _layer(parent, c, scale, tint=None, animate=False, flip_x=False):
    """One creature image/canvas at (0,0), sized 16*scale, full colour (tint
    None) or flattened to the tone `tint`. Non-clickable so it never steals
    taps from a clickable cell.

    Caveat: recolouring an image is all-or-nothing, so a tinted sprite takes
    the tone's fill and skips its outline. The alternative — recolouring at
    partial opacity — would leak the real colours, which is the whole thing
    we are hiding."""
    name = "animals/" + c["img"]
    w = sprite_img(parent, name, scale, flip_x=flip_x)
    if tint is not None:
        w.set_style_image_recolor(lv.color_hex(tint[0]), 0)
        w.set_style_image_recolor_opa(lv.OPA.COVER, 0)
    elif animate and c.get("anim"):
        animate_sprite(w, name, scale, flip_x=flip_x)
    return w


def creature_panel(
    parent,
    c,
    scale,
    reveal=1.0,
    silhouette=False,
    mask=None,
    veil=SIL,
    animate=False,
    flip_x=False,
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
    page); silhouettes and veils hold frame 0 so a mystery stays still.
    `flip_x` mirrors the pixels before drawing, without an LVGL transform."""
    if silhouette or reveal <= 0.0:
        return _layer(parent, c, scale, veil, flip_x=flip_x)
    if reveal >= 1.0:
        return _layer(
            parent,
            c,
            scale,
            mask,
            animate=(animate and mask is None),
            flip_x=flip_x,
        )
    # partial: veiled base + revealed part clipped to the top `reveal`
    px = 16 * scale
    wrap = lv.obj(parent)
    _bare(wrap)
    wrap.set_size(px, px)
    _layer(wrap, c, scale, veil, flip_x=flip_x)
    clip = lv.obj(wrap)
    _bare(clip)
    clip.set_size(px, max(1, int(reveal * px)))
    clip.set_pos(0, 0)
    _layer(clip, c, scale, mask, flip_x=flip_x)
    return wrap
