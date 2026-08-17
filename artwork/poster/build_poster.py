#!/usr/bin/env python3
"""Build the print-ready Vossenjacht A4 poster from project artwork."""

from pathlib import Path
import math
import textwrap

from PIL import Image, ImageDraw, ImageEnhance, ImageFont
from reportlab.graphics.barcode.qr import QrCodeWidget
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas


ROOT = Path(__file__).resolve().parents[2]
OUT_PNG = ROOT / "output" / "poster" / "vossenjacht-poster-a4.png"
OUT_PDF = ROOT / "output" / "pdf" / "vossenjacht-poster-a4.pdf"
BACKGROUND = ROOT / "artwork" / "poster" / "forest-background-generated.png"

W, H = 2480, 3508  # A4 at 300 dpi
INK = "#34271a"
PAPER = "#fff7e6"
CREAM = "#fbf3dd"
GREEN = "#5a9a3c"
GREEN_D = "#3c6b2e"
GOLD = "#e8b23a"
FOCUS = "#ffcb45"
TERRA = "#cf6a3f"
FOREST = "#10200c"

PIXEL_FONT = Path("/Users/fdb/Library/Fonts/Pixelify_Sans/static/PixelifySans-Bold.ttf")
BODY_FONT = Path("/System/Library/Fonts/Supplemental/Arial.ttf")
BODY_BOLD = Path("/System/Library/Fonts/Supplemental/Arial Bold.ttf")


def font(path: Path, size: int):
    return ImageFont.truetype(str(path), size)


def cover(im: Image.Image, size: tuple[int, int]) -> Image.Image:
    scale = max(size[0] / im.width, size[1] / im.height)
    resized = im.resize(
        (round(im.width * scale), round(im.height * scale)), Image.Resampling.LANCZOS
    )
    x = (resized.width - size[0]) // 2
    y = (resized.height - size[1]) // 2
    return resized.crop((x, y, x + size[0], y + size[1]))


def centered(
    draw: ImageDraw.ImageDraw,
    text: str,
    y: int,
    face,
    fill,
    *,
    stroke=0,
    stroke_fill=None,
):
    box = draw.textbbox((0, 0), text, font=face, stroke_width=stroke)
    x = (W - (box[2] - box[0])) // 2
    draw.text(
        (x, y), text, font=face, fill=fill, stroke_width=stroke, stroke_fill=stroke_fill
    )


def wrapped_center(
    draw: ImageDraw.ImageDraw,
    text: str,
    y: int,
    face,
    fill,
    max_width: int,
    spacing: int,
):
    words = text.split()
    lines, current = [], ""
    for word in words:
        candidate = f"{current} {word}".strip()
        if draw.textlength(candidate, font=face) <= max_width:
            current = candidate
        else:
            lines.append(current)
            current = word
    if current:
        lines.append(current)
    for line in lines:
        box = draw.textbbox((0, 0), line, font=face)
        draw.text(((W - (box[2] - box[0])) // 2, y), line, font=face, fill=fill)
        y += spacing
    return y


def rounded_panel(
    canvas_img: Image.Image, box, radius, fill, outline=None, width=1, shadow=18
):
    x0, y0, x1, y1 = box
    layer = Image.new("RGBA", canvas_img.size, (0, 0, 0, 0))
    ld = ImageDraw.Draw(layer)
    if shadow:
        ld.rounded_rectangle(
            (x0 + shadow, y0 + shadow, x1 + shadow, y1 + shadow),
            radius,
            fill=(20, 18, 10, 115),
        )
    ld.rounded_rectangle(box, radius, fill=fill, outline=outline, width=width)
    canvas_img.alpha_composite(layer)


def sprite(path: Path, scale: int) -> Image.Image:
    src = Image.open(path).convert("RGBA")
    return src.resize((src.width * scale, src.height * scale), Image.Resampling.NEAREST)


def qr_image(value: str, module_px: int = 20, border: int = 4) -> Image.Image:
    widget = QrCodeWidget(value, barLevel="H")
    widget.qr.make()
    modules = widget.qr.modules
    count = len(modules)
    size = (count + border * 2) * module_px
    out = Image.new("RGB", (size, size), PAPER)
    qd = ImageDraw.Draw(out)
    for row, values in enumerate(modules):
        for col, dark in enumerate(values):
            if dark:
                x0 = (col + border) * module_px
                y0 = (row + border) * module_px
                qd.rectangle((x0, y0, x0 + module_px - 1, y0 + module_px - 1), fill=INK)
    return out


def paste_screen(canvas_img: Image.Image, path: Path, x: int, y: int, label: str):
    screen_w, screen_h = 680, 510
    outer = (x, y, x + screen_w + 56, y + screen_h + 120)
    rounded_panel(canvas_img, outer, 30, INK, GREEN_D, 8, shadow=16)
    shot = (
        Image.open(path)
        .convert("RGB")
        .resize((screen_w, screen_h), Image.Resampling.NEAREST)
    )
    canvas_img.paste(shot, (x + 28, y + 28))
    d = ImageDraw.Draw(canvas_img)
    label_face = font(PIXEL_FONT, 50)
    box = d.textbbox((0, 0), label, font=label_face)
    d.text(
        (x + (screen_w + 56 - (box[2] - box[0])) // 2, y + screen_h + 48),
        label,
        font=label_face,
        fill=PAPER,
    )


def build_png():
    bg = cover(Image.open(BACKGROUND).convert("RGB"), (W, H))
    bg = ImageEnhance.Color(bg).enhance(0.85).convert("RGBA")
    poster = bg

    # Darken the upper field for title legibility and keep the lower CTA bright.
    overlay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    od = ImageDraw.Draw(overlay)
    od.rectangle((0, 0, W, 1370), fill=(7, 25, 11, 82))
    for y in range(0, H, 14):
        od.rectangle((0, y, W, y + 2), fill=(0, 0, 0, 18))
    poster.alpha_composite(overlay)
    draw = ImageDraw.Draw(poster)

    # Small camp ribbon.
    ribbon = (780, 92, 1700, 214)
    rounded_panel(poster, ribbon, 18, GREEN, GREEN_D, 8, shadow=10)
    ribbon_face = font(PIXEL_FONT, 53)
    rb = draw.textbbox((0, 0), "FRI3D CAMP 2026", font=ribbon_face)
    draw.text(
        ((W - (rb[2] - rb[0])) // 2, 116),
        "FRI3D CAMP 2026",
        font=ribbon_face,
        fill=PAPER,
    )

    title_face = font(PIXEL_FONT, 252)
    centered(draw, "Vossenjacht", 288, title_face, FOREST, stroke=5, stroke_fill=FOREST)
    centered(
        draw, "Vossenjacht", 264, title_face, "#ecff00", stroke=3, stroke_fill="#ecff00"
    )

    tagline = font(PIXEL_FONT, 82)
    centered(draw, "SPOOR DE BEESTEN VAN HET BOS OP.", 594, tagline, FOCUS)

    # Hero fox and a playful parade of discoveries.
    fox = sprite(ROOT / "artwork" / "animals" / "1_vos.png", 31)
    poster.alpha_composite(fox, ((W - fox.width) // 2, 760))
    parade_paths = [
        "1_egel.png",
        "1_axolotl.png",
        "2_slakamander.png",
        "1_konijn.png",
        "2_kameleeuw.png",
        "1_papegaai.png",
    ]
    parade_x = [205, 505, 830, 1420, 1740, 2070]
    for i, (name, x) in enumerate(zip(parade_paths, parade_x)):
        item = sprite(
            ROOT / "artwork" / "animals" / name, 13 if i not in (2, 4) else 11
        )
        poster.alpha_composite(item, (x, 890 + (i % 2) * 70))

    body_face = font(BODY_BOLD, 58)
    centered(draw, "Volg het spoor en vind de geheime dieren.", 1265, body_face, PAPER)
    centered(draw, "Verzorg en deel ze met andere spelers.", 1343, body_face, PAPER)

    # Three real game screens, presented as badge displays.
    screen_y = 1500
    paste_screen(
        poster,
        ROOT / "server" / "static" / "screens" / "jacht.png",
        92,
        screen_y,
        "SPEUR",
    )
    paste_screen(
        poster,
        ROOT / "server" / "static" / "screens" / "beest.png",
        872,
        screen_y,
        "ONTDEK",
    )
    paste_screen(
        poster,
        ROOT / "server" / "static" / "screens" / "boek.png",
        1652,
        screen_y,
        "VERZAMEL",
    )

    # QR call-to-action: calm, high-contrast and large enough for distance scanning.
    cta = (120, 2300, 2360, 3342)
    rounded_panel(poster, cta, 54, GOLD, "#a8761f", 12, shadow=28)
    qr = qr_image("https://foxhunt.enigmeta.com/", module_px=20, border=4)
    qx, qy = 220, 2440
    rounded_panel(
        poster,
        (qx - 34, qy - 34, qx + qr.width + 34, qy + qr.height + 34),
        30,
        PAPER,
        INK,
        10,
        shadow=14,
    )
    poster.paste(qr, (qx, qy))

    cta_x = 1135
    cta_title = font(PIXEL_FONT, 99)
    draw.text((cta_x, 2435), "KLAAR VOOR", font=cta_title, fill=INK)
    draw.text((cta_x, 2535), "DE JACHT?", font=cta_title, fill=INK)
    action = font(PIXEL_FONT, 82)
    button_right = 2235
    draw.rounded_rectangle(
        (cta_x, 2705, button_right, 2865), 24, fill=GREEN_D, outline=INK, width=8
    )
    ab = draw.textbbox((0, 0), "SCAN EN SPEEL!", font=action)
    draw.text(
        (cta_x + (button_right - cta_x - (ab[2] - ab[0])) // 2, 2733),
        "SCAN EN SPEEL!",
        font=action,
        fill=PAPER,
    )

    cta_body = font(BODY_BOLD, 49)
    for i, line in enumerate(
        ("Richt je camera op de QR-code", "en start Vossenjacht op je badge.")
    ):
        draw.text((cta_x, 2935 + i * 70), line, font=cta_body, fill=INK)
    url_face = font(PIXEL_FONT, 40)
    draw.text(
        (cta_x, 3125), "https://foxhunt.enigmeta.com/", font=url_face, fill=GREEN_D
    )

    # Pixel corner details borrowed from the game's UI language.
    for x, y in ((168, 240), (2220, 360), (110, 1180), (2300, 1280), (2020, 2220)):
        draw.rectangle((x - 7, y - 25, x + 7, y + 25), fill=FOCUS)
        draw.rectangle((x - 25, y - 7, x + 25, y + 7), fill=FOCUS)

    OUT_PNG.parent.mkdir(parents=True, exist_ok=True)
    poster.convert("RGB").save(OUT_PNG, quality=96, dpi=(300, 300))


def build_pdf():
    OUT_PDF.parent.mkdir(parents=True, exist_ok=True)
    page_w, page_h = A4
    pdf = canvas.Canvas(str(OUT_PDF), pagesize=A4, pageCompression=1)
    pdf.setTitle("Vossenjacht - Fri3d Camp 2026")
    pdf.setAuthor("Vossenjacht")
    pdf.drawImage(
        str(OUT_PNG),
        0,
        0,
        width=page_w,
        height=page_h,
        preserveAspectRatio=True,
        mask="auto",
    )
    pdf.showPage()
    pdf.save()


if __name__ == "__main__":
    build_png()
    build_pdf()
    print(OUT_PNG)
    print(OUT_PDF)
