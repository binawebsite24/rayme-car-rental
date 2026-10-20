"""Generate the WhatsApp/Open Graph share card and the favicons.

Run via build/build.py. Everything is drawn from the site's own brand tokens
and its own Wix Madefor fonts, so the card matches the page it links to.
"""
import os, sys, site

_usp = site.getusersitepackages()
sys.path[:0] = _usp if isinstance(_usp, list) else [_usp]

from PIL import Image, ImageDraw, ImageFont, ImageFilter

NAVY  = (14, 26, 43)      # #0E1A2B  page background
LIME  = (198, 244, 50)    # #C6F432  accent / wordmark
WHITE = (255, 255, 255)
MUTE  = (184, 196, 212)   # #B8C4D4

W, H = 1200, 630
PAD  = 72

HERE     = os.path.dirname(os.path.abspath(__file__))
PUBLIC   = os.path.join(os.path.dirname(HERE), "public")
FONT_DIR = os.path.join(PUBLIC, "assets", "fonts")


def font(name, size, weight=800):
    """Wix Madefor is a variable font (wght 400-800); pin the axis per use."""
    f = ImageFont.truetype(os.path.join(FONT_DIR, name), size)
    try:
        f.set_variation_by_axes([weight])
    except Exception:
        pass
    return f


def display(size, weight=800):
    return font("wix-madefor-display.woff2", size, weight)


def text(size, weight=500):
    return font("wix-madefor-text.woff2", size, weight)


def tracked(draw, xy, s, fnt, fill, tracking=0):
    """Draw text with letter-spacing; returns the advance width."""
    x, y = xy
    for ch in s:
        draw.text((x, y), ch, font=fnt, fill=fill)
        x += draw.textlength(ch, font=fnt) + tracking
    return x - xy[0] - (tracking if s else 0)


def tracked_width(draw, s, fnt, tracking=0):
    w = sum(draw.textlength(c, font=fnt) for c in s)
    return w + tracking * max(0, len(s) - 1)


def pill(draw, xy, label, fnt, fg, bg, border, pad_x=18, pad_y=11, tracking=1.2):
    x, y = xy
    tw = tracked_width(draw, label, fnt, tracking)
    th = fnt.size
    box = (x, y, x + tw + pad_x * 2, y + th + pad_y * 2)
    r = (box[3] - box[1]) / 2
    draw.rounded_rectangle(box, radius=r, fill=bg, outline=border, width=2)
    tracked(draw, (x + pad_x, y + pad_y - th * 0.14), label, fnt, fg, tracking)
    return box[3] - box[1]


def photo_panel(card, path, left, feather=260):
    """Right-hand car photo, cover-fitted, fading left into the background."""
    img = Image.open(path).convert("RGB")
    pw, ph = W - left, H
    scale = max(pw / img.width, ph / img.height)
    img = img.resize((round(img.width * scale), round(img.height * scale)), Image.LANCZOS)
    ox = (img.width - pw) // 2
    oy = int((img.height - ph) * 0.62)
    img = img.crop((ox, oy, ox + pw, oy + ph))

    mask = Image.new("L", (pw, ph), 255)
    md = ImageDraw.Draw(mask)
    for i in range(feather):
        md.line([(i, 0), (i, ph)], fill=int(255 * (i / feather) ** 1.6))
    mask = mask.filter(ImageFilter.GaussianBlur(10))
    card.paste(img, (left, 0), mask)


def build_card(out_path, hero_photo):
    card = Image.new("RGB", (W, H), NAVY)
    photo_panel(card, hero_photo, left=640)

    # Lime hairline down the left edge — the site's accent rule.
    d = ImageDraw.Draw(card, "RGBA")
    d.rectangle((0, 0, 7, H), fill=LIME)

    y = PAD + 8
    y += pill(d, (PAD, y), "SEKSYEN 13, SHAH ALAM", display(19, 800),
              LIME, (198, 244, 50, 20), (198, 244, 50, 90), tracking=0.2) + 34

    f_rayme = display(132, 800)
    tracked(d, (PAD - 6, y - 14), "RAYME", f_rayme, LIME, -2)
    y += 118

    f_cr = display(68, 800)
    tracked(d, (PAD - 3, y - 8), "CAR RENTAL", f_cr, WHITE, -1)
    y += 86

    tracked(d, (PAD, y), "COMFORTABLE • QUALITY • VALUE", display(18, 800), LIME, 4.2)
    y += 52

    d.text((PAD, y), "Student & worker rates", font=text(29, 500), fill=MUTE)
    y += 40
    f_price = display(34, 800)
    adv = d.textlength("from ", font=text(29, 500))
    d.text((PAD, y + 4), "from ", font=text(29, 500), fill=MUTE)
    d.text((PAD + adv, y - 2), "RM90", font=f_price, fill=LIME)
    adv += d.textlength("RM90", font=f_price)
    d.text((PAD + adv + 6, y + 4), "/day", font=text(29, 500), fill=WHITE)

    # WhatsApp booking chip, bottom-left.
    chip_f = display(21, 800)
    label = "WhatsApp Booking"
    cw = d.textlength(label, font=chip_f)
    cx, cy = PAD, H - PAD - 46
    d.rounded_rectangle((cx, cy, cx + cw + 62, cy + 52), radius=26, fill=LIME)
    bx, by = cx + 20, cy + 15
    d.ellipse((bx, by, bx + 23, by + 22), fill=NAVY)
    d.polygon([(bx + 3, by + 20), (bx + 11, by + 15), (bx + 2, by + 27)], fill=NAVY)
    d.ellipse((bx + 7, by + 9, bx + 10, by + 12), fill=LIME)
    d.ellipse((bx + 12, by + 9, bx + 15, by + 12), fill=LIME)
    d.ellipse((bx + 17, by + 9, bx + 20, by + 12), fill=LIME)
    d.text((cx + 54, cy + 13), label, font=chip_f, fill=NAVY)

    card.save(out_path, "JPEG", quality=86, optimize=True, progressive=True)
    return os.path.getsize(out_path)


def build_icons():
    """Navy tile with a lime R — the mark the design source already used."""
    def tile(size):
        im = Image.new("RGBA", (size, size), NAVY + (255,))
        d = ImageDraw.Draw(im)
        f = display(int(size * 0.68), 800)
        box = d.textbbox((0, 0), "R", font=f)
        d.text(((size - (box[2] - box[0])) / 2 - box[0],
                (size - (box[3] - box[1])) / 2 - box[1]), "R", font=f, fill=LIME)
        return im

    tile(180).save(os.path.join(PUBLIC, "apple-touch-icon.png"))
    tile(512).save(os.path.join(PUBLIC, "icon-512.png"))
    tile(64).save(os.path.join(PUBLIC, "favicon.ico"),
                  sizes=[(16, 16), (32, 32), (48, 48), (64, 64)])


def main():
    os.makedirs(os.path.join(PUBLIC, "assets", "social"), exist_ok=True)
    out = os.path.join(PUBLIC, "assets", "social", "share-card.jpg")
    size = build_card(out, os.path.join(PUBLIC, "assets", "images", "axia-white.jpg"))
    build_icons()
    print("  share-card.jpg  %.0f KB  (1200x630)" % (size / 1024))


if __name__ == "__main__":
    main()
