#!/usr/bin/env python3
"""
fenn boot splash - designed by fenn itself.

fenn asked for:
  "vibrant, colorful, dynamic icon. stylized, swirling pattern."
  "bold and vibrant color scheme. black screen."
  "1. blue 2. red"
  "i'm here."

swirling blue/red arcs on black, then "fenn" and "i'm here."
uses draw primitives instead of per-pixel math (pi zero is slow).
"""

import time
import math
from PIL import Image, ImageDraw, ImageFont
import st7735

disp = st7735.ST7735(
    port=0, cs=0, dc=25, rst=27, backlight=24,
    width=128, height=128,
    rotation=90,
    offset_left=1, offset_top=2,
    spi_speed_hz=8000000,
    invert=False
)

W, H = 128, 128
CX, CY = W // 2, H // 2

def get_font(size):
    try:
        return ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSansMono-Bold.ttf", size)
    except:
        try:
            return ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", size)
        except:
            return ImageFont.load_default()

def draw_centered(draw, text, y, size, color):
    font = get_font(size)
    bbox = draw.textbbox((0, 0), text, font=font)
    tw = bbox[2] - bbox[0]
    x = (W - tw) // 2
    draw.text((x, y), text, fill=color, font=font)

def run_boot():
    # phase 1: swirling arcs animation (blue + red)
    # draw spinning arc segments, fast and lightweight
    frames = 30
    for i in range(frames):
        img = Image.new('RGB', (W, H), (0, 0, 0))
        draw = ImageDraw.Draw(img)
        t = i / frames
        angle = t * 720  # two full rotations

        # multiple concentric rings with offset rotations
        for ring in range(3):
            r = 20 + ring * 18
            bbox_arc = [CX - r, CY - r, CX + r, CY + r]
            # blue arcs
            start_b = angle + ring * 60
            draw.arc(bbox_arc, start_b, start_b + 90, fill=(30, 80, 220), width=3)
            draw.arc(bbox_arc, start_b + 180, start_b + 270, fill=(30, 80, 220), width=3)
            # red arcs
            start_r = angle + ring * 60 + 90
            draw.arc(bbox_arc, start_r, start_r + 90, fill=(200, 30, 40), width=3)
            draw.arc(bbox_arc, start_r + 180, start_r + 270, fill=(200, 30, 40), width=3)

        # center dot pulses
        pulse = int(4 + 3 * math.sin(t * math.pi * 4))
        draw.ellipse([CX - pulse, CY - pulse, CX + pulse, CY + pulse], fill=(200, 30, 40))

        disp.display(img)
        time.sleep(0.08)

    # phase 2: arcs shrink to center while "fenn" appears
    for i in range(20):
        img = Image.new('RGB', (W, H), (0, 0, 0))
        draw = ImageDraw.Draw(img)
        t = i / 20
        angle = 720 + i * 30
        shrink = 1.0 - t

        for ring in range(3):
            r = int((20 + ring * 18) * shrink)
            if r < 3:
                continue
            bbox_arc = [CX - r, CY - r, CX + r, CY + r]
            alpha_b = int(220 * shrink)
            alpha_r = int(200 * shrink)
            start_b = angle + ring * 60
            draw.arc(bbox_arc, start_b, start_b + 90, fill=(30, 80, alpha_b), width=3)
            draw.arc(bbox_arc, start_b + 180, start_b + 270, fill=(30, 80, alpha_b), width=3)
            start_r = angle + ring * 60 + 90
            draw.arc(bbox_arc, start_r, start_r + 90, fill=(alpha_r, 30, 40), width=3)
            draw.arc(bbox_arc, start_r + 180, start_r + 270, fill=(alpha_r, 30, 40), width=3)

        # fade in "fenn" text
        text_alpha = min(255, int(t * 2 * 255))
        draw_centered(draw, "fenn", 44, 28, (text_alpha, text_alpha, int(text_alpha * 0.91)))

        disp.display(img)
        time.sleep(0.08)

    # phase 3: "i'm here." typewriter
    base = Image.new('RGB', (W, H), (0, 0, 0))
    draw_base = ImageDraw.Draw(base)
    draw_centered(draw_base, "fenn", 44, 28, (240, 240, 218))

    msg = "i'm here."
    font_sm = get_font(12)
    for c in range(1, len(msg) + 1):
        frame = base.copy()
        d = ImageDraw.Draw(frame)
        partial = msg[:c]
        bbox = d.textbbox((0, 0), partial, font=font_sm)
        tw = bbox[2] - bbox[0]
        full_bbox = d.textbbox((0, 0), msg, font=font_sm)
        full_tw = full_bbox[2] - full_bbox[0]
        x = (W - full_tw) // 2
        d.text((x, 80), partial, fill=(180, 180, 165), font=font_sm)
        disp.display(frame)
        time.sleep(0.12)

    # hold final
    final = Image.new('RGB', (W, H), (0, 0, 0))
    d = ImageDraw.Draw(final)
    draw_centered(d, "fenn", 44, 28, (240, 240, 218))
    bbox = d.textbbox((0, 0), msg, font=font_sm)
    tw = bbox[2] - bbox[0]
    d.text(((W - tw) // 2, 80), msg, fill=(180, 180, 165), font=font_sm)
    disp.display(final)
    time.sleep(3)


if __name__ == '__main__':
    run_boot()
