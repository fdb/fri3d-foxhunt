# ui.py — shared look & helpers: colours, pixel fonts, positioned widgets,
# and focus wiring so touch/mouse AND joystick/arrow-keys all work.
#
# Everything is positioned with absolute integer coords from the layout spec
# (layout/foxhunt-layout.html), in the real 320x240 space.

import lvgl as lv
from mpos import FontManager

# ---- design palette (hex) ------------------------------------------------
INK = 0x34271A
PAPER = 0xEFE0BB
CARD = 0xFBF3DD
GREEN = 0x5A9A3C
GREEN_D = 0x3C6B2E
GOLD = 0xE8B23A
GOLD_D = 0xA8761F
TERRA = 0xCF6A3F
TERRA_D = 0x9C4422
CREAM = 0xFFF7E6

# Semantic / surface tokens — promoted from inline literals so the look lives in
# one place. SURFACE_SOFT is the pale card interior on the beast/hunt screens;
# DORMANT is the sleeping-cell bg (was also written out as the _TRACK literal).
TEXT_MUTED = 0x5E6B44  # secondary text (found-facts, captions)
MYSTERY = 0x8A7D5E  # the "???" label on an uncaught creature
SURFACE_SOFT = 0xE9F1CF  # card interior (portrait card, hunt/win panel)
SURFACE_TINT = 0xEEF4D6  # lighter card interior (code reveal, feed stage, weetje)
DORMANT = 0xD8C9A4  # sleeping-cell bg / empty-segment track
BORDER_REST = 0xCDB67D  # quiet tan frame on every unfocused grid cell
FOCUS_GOLD = 0xFFCB45  # bright gold halo drawn around the focused widget

# Spacing & geometry scale — replaces scattered magic 2/3/5/6 in the screens.
GAP_S = 3
GAP_M = 6
PAD = 8
RADIUS = 2
BORDER = 2
BORDER_THIN = 1

# Focus ring geometry. Focus is signalled on three channels at once — contrast
# (the widget's own frame goes from pale tan to full ink), hue (a gold halo) and
# thickness (a 2px frame becomes a 6px / 4px double ring). One channel alone
# (the old "recolour the border a bit goldener") reads as noise on a 320x240
# screen full of warm tans.
HALO = 4  # gold halo on roomy widgets (standalone buttons, keypad)
HALO_TIGHT = 2  # halo that still fits the 4px gutter between grid cells
ROW_SLACK = 4  # slack a flex row keeps around itself so halos aren't clipped


def hexc(v):
    return lv.color_hex(v)


# ---- shared styles -------------------------------------------------------
# LVGL best practice: define reusable lv.style_t once and add_style() them,
# rather than re-setting the same properties inline on every widget (each inline
# set grows that object's private local-style store). These are created at
# import — lvgl is already initialised by MicroPythonOS before the app loads.
#
# bg colour and radius stay *local* per widget (they vary per call and a local
# property always overrides a shared one), so only the truly common bits live
# here: the box reset, the panel outline, the segment-cell hairline, and the
# focus / pressed state styles that used to be re-applied on every nav widget.


def _style(**props):
    s = lv.style_t()
    s.init()
    if "pad_all" in props:
        s.set_pad_all(props["pad_all"])
    if "border_width" in props:
        s.set_border_width(props["border_width"])
    if "border_color" in props:
        s.set_border_color(hexc(props["border_color"]))
    if "radius" in props:
        s.set_radius(props["radius"])
    if "outline_color" in props:
        s.set_outline_color(hexc(props["outline_color"]))
    if "outline_width" in props:
        s.set_outline_width(props["outline_width"])
    if "outline_pad" in props:
        s.set_outline_pad(props["outline_pad"])
    if "outline_opa" in props:
        s.set_outline_opa(props["outline_opa"])
    if "translate_y" in props:
        s.set_translate_y(props["translate_y"])
    return s


# box reset: kill the theme's default padding + border on every plain container.
_RESET = _style(pad_all=0, border_width=0)
# panel outline: the hard ink frame shared by every design "Panel".
_PANEL = _style(border_width=BORDER, border_color=INK)
# segment cell: the 1px ink hairline around each LED/meter cell.
_SEG_CELL = _style(border_width=BORDER_THIN, border_color=INK)
# focus ring for joystick/arrow nav (added on the FOCUSED state): the widget's
# frame snaps to full ink and a thick gold halo is drawn just outside it. Dark
# edge against bright halo is the highest-contrast pair the palette has, and the
# ring goes from 2px to 6px — visible at a glance, from across a room.
_FOCUS = _style(
    border_color=INK,
    outline_color=FOCUS_GOLD,
    outline_width=HALO,
    outline_pad=0,
    outline_opa=lv.OPA.COVER,
)
# Same treatment, tighter halo: for widgets packed in a grid (the collection
# cells, the beast/feed action rows) a 4px halo would jump the gutter and touch
# the neighbour, so it stays at HALO_TIGHT and the gutter keeps a clear 2px.
# The border only *recolours* (width stays BORDER) because border width insets
# the content area — growing it would nudge the cell's sprite and label by a
# pixel. Every cell reserves a BORDER-wide tan frame (BORDER_REST) at rest;
# FOCUSED-state specificity outranks that local default-state border, so ink
# wins while focused and the tan returns when focus moves on.
_FOCUS_BORDER = _style(
    border_width=BORDER,
    border_color=INK,
    outline_color=FOCUS_GOLD,
    outline_width=HALO_TIGHT,
    outline_pad=0,
    outline_opa=lv.OPA.COVER,
)
# tactile press: nudge an actionable widget down 2px on the PRESSED state.
_PRESSED = _style(translate_y=2)


# ---- fonts: baked Pixelify Sans bitmap fonts (crisp, no anti-alias) --------
# Loaded at runtime via lv.binfont_create (.bin from lv_font_conv). Falls back
# to built-in Montserrat if a font fails to load, so the app always runs.
_FONT_DIR = "M:apps/be.fri3d.foxhunt/assets/fonts/"
_FONTS = {}


def _load(name, fallback_size):
    if name in _FONTS:
        return _FONTS[name]
    f = None
    try:
        f = lv.binfont_create(_FONT_DIR + name)
    except Exception as e:
        print("ui: binfont", name, "failed:", e)
    if f is None:
        try:
            f = FontManager.getFont(size=fallback_size)
        except Exception:
            f = None
    _FONTS[name] = f
    return f


def font_small():
    return _load("pixelify_r11.bin", 11)


def font_label():
    return _load("pixelify_r11.bin", 11)


def font_title():
    return _load("pixelify_b22.bin", 20)


# ---- positioned widget helpers -------------------------------------------
def make_screen(bg):
    s = lv.obj()
    s.add_style(_RESET, 0)
    s.set_style_radius(0, 0)
    s.set_style_bg_color(hexc(bg), 0)
    s.remove_flag(lv.obj.FLAG.SCROLLABLE)
    return s


def box(parent, x, y, w, h, bg=None, radius=0):
    o = lv.obj(parent)
    o.set_pos(x, y)
    o.set_size(w, h)
    o.add_style(_RESET, 0)  # shared pad/border reset
    o.set_style_radius(radius, 0)  # radius varies per call -> local
    o.remove_flag(lv.obj.FLAG.SCROLLABLE)
    if bg is None:
        o.set_style_bg_opa(lv.OPA.TRANSP, 0)
    else:
        o.set_style_bg_color(hexc(bg), 0)
    return o


def label(parent, text, x, y, color=INK, font=None, w=None, center=False):
    l = lv.label(parent)
    l.set_text(text)
    l.set_pos(x, y)
    if w is not None:
        l.set_width(w)
        if center:
            l.set_style_text_align(lv.TEXT_ALIGN.CENTER, 0)
    l.set_style_text_color(hexc(color), 0)
    f = font if font is not None else font_label()
    if f is not None:
        l.set_style_text_font(f, 0)
    return l


def banner(screen, title, color=GREEN, right=None):
    # No back button: MicroPythonOS provides a global left-edge back swipe
    # (main.py handle_back_swipe) plus Esc / joystick. Apps don't draw their own.
    box(screen, 0, 0, 320, 26, color)
    label(screen, title, 8, 4, CREAM, font_title())
    if right is not None:
        label(screen, right, 240, 8, CREAM, font_small(), w=72, center=True)


import art

_TRACK = DORMANT  # empty-segment / track colour (same value, named token)


def panel(parent, x, y, w, h, bg=CARD, radius=RADIUS, border=INK, bw=BORDER):
    """A pixel panel: filled box with a hard ink outline (design 'Panel')."""
    o = box(parent, x, y, w, h, bg, radius=radius)
    if bw == BORDER and border == INK:
        o.add_style(_PANEL, 0)  # shared ink outline (common case)
    elif bw:
        o.set_style_border_width(bw, 0)  # custom width/colour -> local
        o.set_style_border_color(hexc(border), 0)
    return o


def row(parent, x, y, w, h, gap=GAP_M, wrap=False, bg=None):
    """A flex container laying children left-to-right with `gap` between them,
    so callers stop computing `x = base + i*(w+gap)`. wrap=True flows onto
    multiple lines (a grid). Children are added with pos (0,0) — flex places
    them. Give a wrap container a few px of slack so an exact-fit last column
    doesn't wrap early.

    The container is grown by ROW_SLACK on every side and given matching
    padding, so children still land on the caller's coordinates but a focus halo
    drawn outside a child isn't clipped away at the container edge."""
    o = box(
        parent, x - ROW_SLACK, y - ROW_SLACK, w + 2 * ROW_SLACK, h + 2 * ROW_SLACK, bg
    )
    o.set_style_pad_all(ROW_SLACK, 0)
    o.set_flex_flow(lv.FLEX_FLOW.ROW_WRAP if wrap else lv.FLEX_FLOW.ROW)
    o.set_style_pad_column(gap, 0)
    o.set_style_pad_row(gap, 0)
    return o


def seg_bar(
    parent, x, y, text, lit, color, total=5, seg_w=16, seg_h=11, gap=GAP_S, label_w=56
):
    """Label + a row of `total` segment cells, `lit` of them coloured. Mirrors
    the device's 5-LED look. Returns the list of cells for live updates."""
    label(parent, text, x, y, INK, font_small())
    track = row(
        parent, x + label_w, y, total * seg_w + (total - 1) * gap, seg_h, gap=gap
    )
    cells = []
    for i in range(total):
        c = box(track, 0, 0, seg_w, seg_h, color if i < lit else _TRACK)
        c.add_style(_SEG_CELL, 0)  # shared 1px ink hairline
        cells.append(c)
    return cells


def set_segments(cells, lit, color):
    for i, c in enumerate(cells):
        c.set_style_bg_color(hexc(color if i < lit else _TRACK), 0)


def heart_row(parent, x, y, filled, total=5, scale=2, gap=GAP_S):
    """A row of pixel hearts, `filled` red and the rest greyed out."""
    hw = 9 * scale
    track = row(parent, x, y, total * hw + (total - 1) * gap, 8 * scale, gap=gap)
    hearts = []
    for i in range(total):
        pal = (
            {"k": 0x7A1F12, "r": 0xE0463A}
            if i < filled
            else {"k": 0xB0A07E, "r": 0xECE0C2}
        )
        hearts.append(art.draw_sprite(track, art.HEART, pal, scale))
    return hearts


def focusable(obj, on_click=None, focus_border=False):
    """Make an obj tap/click/arrow-key activatable, give it a gold focus ring
    (for joystick/arrow nav), and register it in the default LVGL group.

    focus_border=True recolours the widget's own border to gold instead of
    drawing the default outer outline — use it for widgets in a tight grid
    (the collection cells) where an outer ring would overlap neighbours."""
    obj.add_flag(lv.obj.FLAG.CLICKABLE)
    # Shared state styles instead of four inline setters per nav widget.
    obj.add_style(
        _FOCUS_BORDER if focus_border else _FOCUS, lv.PART.MAIN | lv.STATE.FOCUSED
    )
    g = lv.group_get_default()
    if g:
        g.add_obj(obj)
    if on_click is not None:
        # Tactile press feedback only on things that actually do something.
        obj.add_style(_PRESSED, lv.PART.MAIN | lv.STATE.PRESSED)
        obj.add_event_cb(lambda e: on_click(), lv.EVENT.CLICKED, None)
    return obj
