# ui.py — shared look & helpers: colours, pixel fonts, positioned widgets,
# and focus wiring so touch/mouse AND joystick/arrow-keys all work.
#
# Everything is positioned with absolute integer coords from the layout spec
# (layout/beestenjacht-layout.html), in the real 320x240 space.

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


def hexc(v):
    return lv.color_hex(v)


# ---- fonts (built-in Montserrat for now; swap to baked Pixelify later) ----
_FONTS = {}


def _font(size):
    if size in _FONTS:
        return _FONTS[size]
    f = None
    try:
        f = FontManager.getFont(size=size)
    except Exception as e:
        print("ui: font", size, "failed:", e)
    _FONTS[size] = f
    return f


def font_title():
    return _font(20)


def font_label():
    return _font(14)


# ---- positioned widget helpers -------------------------------------------
def make_screen(bg):
    s = lv.obj()
    s.set_style_pad_all(0, 0)
    s.set_style_border_width(0, 0)
    s.set_style_radius(0, 0)
    s.set_style_bg_color(hexc(bg), 0)
    s.remove_flag(lv.obj.FLAG.SCROLLABLE)
    return s


def box(parent, x, y, w, h, bg=None, radius=0):
    o = lv.obj(parent)
    o.set_pos(x, y)
    o.set_size(w, h)
    o.set_style_pad_all(0, 0)
    o.set_style_border_width(0, 0)
    o.set_style_radius(radius, 0)
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


def banner(screen, title, color=GREEN, right=None, back=False):
    box(screen, 0, 0, 320, 26, color)
    label(screen, ("< " + title) if back else title, 8, 4, CREAM, font_title())
    if right is not None:
        label(screen, right, 240, 7, CREAM, font_label(), w=72, center=True)


def focusable(obj, on_click=None):
    """Make an obj tap/click/arrow-key activatable with a focus outline, and
    register it in the default LVGL group (where the board's indevs deliver)."""
    obj.add_flag(lv.obj.FLAG.CLICKABLE)
    obj.set_style_outline_width(3, lv.STATE.FOCUSED)
    obj.set_style_outline_color(hexc(0xFFFFFF), lv.STATE.FOCUSED)
    obj.set_style_outline_opa(lv.OPA.COVER, lv.STATE.FOCUSED)
    g = lv.group_get_default()
    if g:
        g.add_obj(obj)
    if on_click is not None:
        obj.add_event_cb(lambda e: on_click(), lv.EVENT.CLICKED, None)
    return obj
