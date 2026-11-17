#!/usr/bin/env python3
"""tlm lcd display, ST7735S 128x128 Waveshare 1.44in HAT."""
import st7735
from PIL import Image, ImageDraw, ImageFont
import subprocess
import sys
import time
import threading

# hardware
SPI_PORT = 0
SPI_CS = 0
DC_PIN = 25
BL_PIN = 24
RST_PIN = 27
WIDTH = 128
HEIGHT = 128
ROTATION = 90
SPI_SPEED = 8000000

# offset fix for rainbow edge pixels
OFFSET_LEFT = 1
OFFSET_TOP = 2

# palette
BG = (0, 0, 0)
GREEN = (0, 255, 65)
DIM_GREEN = (0, 120, 30)
DARK_GREEN = (0, 60, 15)
GREY = (60, 60, 60)
DARK_GREY = (30, 30, 30)
WHITE = (200, 200, 200)
ACCENT = (0, 200, 55)


def get_display():
    return st7735.ST7735(
        port=SPI_PORT, cs=SPI_CS, dc=DC_PIN,
        backlight=BL_PIN, rst=RST_PIN,
        width=WIDTH, height=HEIGHT, rotation=ROTATION,
        invert=False, spi_speed_hz=SPI_SPEED,
        offset_left=OFFSET_LEFT, offset_top=OFFSET_TOP,
    )


def font(size):
    try:
        return ImageFont.truetype(
            "/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf", size)
    except:
        return ImageFont.load_default()


def wrap(text, f, max_w, draw):
    words = text.split()
    lines = []
    cur = ""
    for w in words:
        test = f"{cur} {w}".strip()
        if draw.textbbox((0, 0), test, font=f)[2] > max_w:
            if cur:
                lines.append(cur)
            cur = w
        else:
            cur = test
    if cur:
        lines.append(cur)
    return lines


def draw_header(draw, text, y=0):
    """thin top bar with label."""
    draw.rectangle([(0, y), (WIDTH, y + 14)], fill=(0, 30, 10))
    draw.text((4, y + 1), text, fill=DIM_GREEN, font=font(10))
    draw.line([(0, y + 14), (WIDTH, y + 14)], fill=DARK_GREEN, width=1)
    return y + 16


def show_boot(disp):
    img = Image.new("RGB", (WIDTH, HEIGHT), BG)
    draw = ImageDraw.Draw(img)

    # top accent line
    draw.line([(0, 0), (WIDTH, 0)], fill=GREEN, width=1)

    # centered title
    t = font(22)
    draw.text((34, 28), "tlm", fill=GREEN, font=t)

    # subtitle
    s = font(8)
    draw.text((16, 56), "tiny language model", fill=DIM_GREEN, font=s)

    # specs box
    draw.rectangle([(10, 72), (118, 112)], outline=DARK_GREEN, width=1)
    draw.text((14, 76), "smollm2-135m q4", fill=GREY, font=s)
    draw.text((14, 88), "pi zero 2 w", fill=GREY, font=s)
    draw.text((14, 100), "512mb / no gpu", fill=GREY, font=s)

    # bottom accent
    draw.line([(0, 127), (WIDTH, 127)], fill=DARK_GREEN, width=1)

    disp.display(img)


def show_prompt(disp, prompt):
    img = Image.new("RGB", (WIDTH, HEIGHT), BG)
    draw = ImageDraw.Draw(img)

    y = draw_header(draw, "input")

    f = font(10)
    lines = wrap(prompt, f, WIDTH - 12, draw)
    for line in lines:
        draw.text((6, y), line, fill=GREEN, font=f)
        y += 13
        if y > HEIGHT - 10:
            break

    # blinking cursor
    draw.rectangle([(6, y + 2), (12, y + 10)], fill=GREEN)

    disp.display(img)


def show_thinking(disp, prompt, frame=0):
    img = Image.new("RGB", (WIDTH, HEIGHT), BG)
    draw = ImageDraw.Draw(img)

    # header with prompt
    trunc = prompt if len(prompt) <= 20 else prompt[:17] + "..."
    y = draw_header(draw, "> " + trunc)

    # center area, spiral
    import math
    cx, cy = 64, 54
    angle = frame * 12
    for ring in range(3):
        r = 8 + ring * 9
        bbox = [cx - r, cy - r, cx + r, cy + r]
        sb = angle + ring * 60
        draw.arc(bbox, sb, sb + 90, fill=(30, 80, 220), width=2)
        draw.arc(bbox, sb + 180, sb + 270, fill=(30, 80, 220), width=2)
        sr = angle + ring * 60 + 90
        draw.arc(bbox, sr, sr + 90, fill=(200, 30, 40), width=2)
        draw.arc(bbox, sr + 180, sr + 270, fill=(200, 30, 40), width=2)
    pulse = int(2 + 1.5 * math.sin(frame * 0.3))
    draw.ellipse([cx - pulse, cy - pulse, cx + pulse, cy + pulse], fill=(200, 30, 40))

    # "processing..." label centered
    s = font(8)
    n = frame % 4
    label = "processing" + "." * n
    bb = draw.textbbox((0, 0), label, font=s)
    lw = bb[2] - bb[0]
    draw.text(((128 - lw) // 2, 84), label, fill=DIM_GREEN, font=s)

    # bottom bar with elapsed
    elapsed = frame * 0.25
    draw.rectangle([(0, 114), (WIDTH, 128)], fill=(0, 20, 8))
    draw.line([(0, 114), (WIDTH, 114)], fill=DARK_GREEN, width=1)

    # elapsed left, model right
    draw.text((4, 116), f"{elapsed:.1f}s", fill=GREY, font=s)
    draw.text((76, 116), "135m q4", fill=DARK_GREY, font=s)

    disp.display(img)


def show_response(disp, prompt, response):
    img = Image.new("RGB", (WIDTH, HEIGHT), BG)
    draw = ImageDraw.Draw(img)

    trunc = prompt if len(prompt) <= 20 else prompt[:17] + "..."
    y = draw_header(draw, "> " + trunc)

    f = font(10)
    lines = wrap(response, f, WIDTH - 12, draw)
    for line in lines:
        draw.text((6, y), line, fill=GREEN, font=f)
        y += 13
        if y > HEIGHT - 16:
            break

    # bottom bar
    draw.rectangle([(0, 114), (WIDTH, 128)], fill=(0, 20, 8))
    draw.line([(0, 114), (WIDTH, 114)], fill=DARK_GREEN, width=1)
    s = font(8)
    draw.text((4, 116), "done", fill=DIM_GREEN, font=s)
    clen = len(response.split())
    draw.text((72, 116), f"{clen} words", fill=GREY, font=s)

    disp.display(img)


def show_typing(disp, prompt, response):
    """typewriter reveal."""
    f = font(10)
    s = font(8)
    trunc = prompt if len(prompt) <= 20 else prompt[:17] + "..."

    total = len(response)
    step = max(1, total // 25)
    shown = 0

    while shown < total:
        shown = min(shown + step, total)
        partial = response[:shown]

        img = Image.new("RGB", (WIDTH, HEIGHT), BG)
        draw = ImageDraw.Draw(img)

        y = draw_header(draw, "> " + trunc)

        lines = wrap(partial, f, WIDTH - 12, draw)
        last_x = 6
        for line in lines:
            draw.text((6, y), line, fill=GREEN, font=f)
            last_x = 6 + draw.textbbox((0, 0), line, font=f)[2]
            y += 13
            if y > HEIGHT - 16:
                break

        # cursor block
        if shown < total:
            cy = y - 13
            draw.rectangle([(last_x + 1, cy + 2), (last_x + 7, cy + 10)], fill=GREEN)

        # bottom bar
        draw.rectangle([(0, 114), (WIDTH, 128)], fill=(0, 20, 8))
        draw.line([(0, 114), (WIDTH, 114)], fill=DARK_GREEN, width=1)
        pct = int(100 * shown / total)
        draw.text((4, 116), f"{pct}%", fill=GREY, font=s)

        disp.display(img)
        time.sleep(0.04)


def run_tlm(prompt):
    result = subprocess.run(
        ["python3", "tlm.py", prompt],
        capture_output=True, text=True, timeout=120,
        cwd="/home/walmart"
    )
    return result.stdout.strip()


def ask(disp, prompt):
    """full pipeline: prompt, thinking spinner, inference, typewriter, final."""
    show_prompt(disp, prompt)
    time.sleep(0.8)

    result = [None]
    def do_infer():
        result[0] = run_tlm(prompt)

    t = threading.Thread(target=do_infer)
    t.start()

    frame = 0
    while t.is_alive():
        show_thinking(disp, prompt, frame)
        frame += 1
        time.sleep(0.25)
    t.join()

    response = result[0] or "no response."
    print(f"Q: {prompt}")
    print(f"A: {response}")
    print()

    show_typing(disp, prompt, response)
    show_response(disp, prompt, response)
    return response


def interactive():
    disp = get_display()
    show_boot(disp)
    time.sleep(2)
    print("tlm lcd interactive. type quit to exit.")
    print("---")
    while True:
        try:
            prompt = input("> ")
            if prompt.lower() in ("quit", "exit", "q"):
                break
            ask(disp, prompt)
        except (KeyboardInterrupt, EOFError):
            break
    disp.display(Image.new("RGB", (WIDTH, HEIGHT), BG))


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] in ("-i", "--interactive"):
        interactive()
    elif len(sys.argv) > 1 and sys.argv[1] == "--boot":
        disp = get_display()
        show_boot(disp)
    elif len(sys.argv) > 1:
        disp = get_display()
        ask(disp, " ".join(sys.argv[1:]))
    else:
        disp = get_display()
        show_boot(disp)
        print("tlm lcd ready. use -i for interactive or pass a question.")
