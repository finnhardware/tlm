#!/usr/bin/env python3
"""display tlm output on SPI LCD hat."""
import sys
import re

try:
    from PIL import Image, ImageDraw, ImageFont
except ImportError:
    print("need: pip install Pillow")
    exit(1)

WIDTH = 240
HEIGHT = 240
FONT_SIZE = 16
MARGIN = 8
BG = (0, 0, 0)
FG = (0, 255, 0)


def wrap_text(text, font, max_width, draw):
    words = text.split()
    lines = []
    current = ""
    for word in words:
        test = f"{current} {word}".strip()
        bbox = draw.textbbox((0, 0), test, font=font)
        if bbox[2] - bbox[0] > max_width:
            if current:
                lines.append(current)
            current = word
        else:
            current = test
    if current:
        lines.append(current)
    return lines


def render(text):
    img = Image.new("RGB", (WIDTH, HEIGHT), BG)
    draw = ImageDraw.Draw(img)
    try:
        font = ImageFont.truetype(
            "/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf", FONT_SIZE)
    except Exception:
        font = ImageFont.load_default()

    lines = wrap_text(text, font, WIDTH - MARGIN * 2, draw)
    y = MARGIN
    for line in lines:
        draw.text((MARGIN, y), line, fill=FG, font=font)
        y += FONT_SIZE + 4
        if y > HEIGHT - MARGIN:
            break
    return img


if __name__ == "__main__":
    text = " ".join(sys.argv[1:]) if len(sys.argv) > 1 else "tlm ready."
    img = render(text)
    img.save("/tmp/tlm_display.png")
    print(f"rendered to /tmp/tlm_display.png")
