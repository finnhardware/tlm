#!/usr/bin/env python3
"""tlm lcd display — ST7735S 128x128 Waveshare 1.44in HAT."""
import st7735
from PIL import Image, ImageDraw, ImageFont
import subprocess
import sys
import time
import threading

# hardware config
SPI_PORT = 0
SPI_CS = 0
DC_PIN = 25
BL_PIN = 24
RST_PIN = 27
WIDTH = 128
HEIGHT = 128
ROTATION = 90
SPI_SPEED = 8000000

# colors
BG = (0, 0, 0)
GREEN = (0, 255, 0)
DIM_GREEN = (0, 100, 0)
PROMPT_COLOR = (80, 80, 80)
THINKING_COLOR = (0, 180, 0)
CURSOR = (0, 255, 0)

FONT_SM = 10
FONT_MD = 12
FONT_LG = 14


def get_display():
    return st7735.ST7735(
        port=SPI_PORT, cs=SPI_CS, dc=DC_PIN,
        backlight=BL_PIN, rst=RST_PIN,
        width=WIDTH, height=HEIGHT, rotation=ROTATION,
        invert=False, spi_speed_hz=SPI_SPEED,
        offset_left=2, offset_top=1,
    )


def get_font(size):
    try:
        return ImageFont.truetype(
            "/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf", size)
    except:
        return ImageFont.load_default()


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


def show_boot(disp):
    """boot screen."""
    img = Image.new("RGB", (WIDTH, HEIGHT), BG)
    draw = ImageDraw.Draw(img)
    font = get_font(FONT_LG)
    sfont = get_font(FONT_SM)

    draw.text((20, 40), "tlm", fill=GREEN, font=get_font(24))
    draw.text((10, 75), "tiny language model", fill=DIM_GREEN, font=sfont)
    draw.text((10, 90), "smollm2-135m", fill=PROMPT_COLOR, font=sfont)
    draw.text((10, 105), "pi zero 2 w", fill=PROMPT_COLOR, font=sfont)

    disp.display(img)


def show_prompt(disp, prompt):
    """show the user's question."""
    img = Image.new("RGB", (WIDTH, HEIGHT), BG)
    draw = ImageDraw.Draw(img)
    font = get_font(FONT_SM)

    # header
    draw.text((4, 2), "> input", fill=DIM_GREEN, font=font)
    draw.line([(4, 14), (124, 14)], fill=DIM_GREEN, width=1)

    # prompt text
    lines = wrap_text(prompt, font, WIDTH - 10, draw)
    y = 20
    for line in lines:
        draw.text((5, y), line, fill=GREEN, font=font)
        y += 13
        if y > HEIGHT - 15:
            break

    disp.display(img)


def show_thinking(disp, prompt, frame=0):
    """thinking animation frame."""
    img = Image.new("RGB", (WIDTH, HEIGHT), BG)
    draw = ImageDraw.Draw(img)
    font = get_font(FONT_SM)

    # prompt at top (dim)
    draw.text((4, 2), "> " + prompt[:18], fill=PROMPT_COLOR, font=font)
    draw.line([(4, 14), (124, 14)], fill=(0, 50, 0), width=1)

    # thinking animation - spinning dots
    cx, cy = 64, 55
    dots = "⠋⠙⠹⠸⠼⠴⠦⠧⠇⠏"
    spinner = dots[frame % len(dots)]

    big_font = get_font(FONT_LG)
    draw.text((45, 45), "thinking", fill=THINKING_COLOR, font=get_font(FONT_SM))

    # animated dots
    num_dots = (frame % 4)
    dot_str = "." * num_dots
    draw.text((50, 60), dot_str, fill=GREEN, font=get_font(20))

    # bottom bar - elapsed time
    elapsed = frame * 0.3
    draw.text((4, 115), f"{elapsed:.1f}s", fill=PROMPT_COLOR, font=font)

    # pulsing block cursor
    if frame % 2 == 0:
        draw.rectangle([(100, 60), (108, 72)], fill=GREEN)

    disp.display(img)


def show_response(disp, prompt, response):
    """show the final response."""
    img = Image.new("RGB", (WIDTH, HEIGHT), BG)
    draw = ImageDraw.Draw(img)
    font = get_font(FONT_SM)

    # prompt at top (dim, truncated)
    trunc = prompt if len(prompt) <= 20 else prompt[:17] + "..."
    draw.text((4, 2), "> " + trunc, fill=PROMPT_COLOR, font=font)
    draw.line([(4, 14), (124, 14)], fill=DIM_GREEN, width=1)

    # response text
    lines = wrap_text(response, font, WIDTH - 10, draw)
    y = 20
    for line in lines:
        draw.text((5, y), line, fill=GREEN, font=font)
        y += 13
        if y > HEIGHT - 5:
            break

    disp.display(img)


def show_typing(disp, prompt, response):
    """typewriter effect — reveal response char by char."""
    font = get_font(FONT_SM)

    # truncated prompt for header
    trunc = prompt if len(prompt) <= 20 else prompt[:17] + "..."

    chars_shown = 0
    total = len(response)
    step = max(1, total // 20)  # ~20 frames to type out

    while chars_shown < total:
        chars_shown = min(chars_shown + step, total)
        partial = response[:chars_shown]

        img = Image.new("RGB", (WIDTH, HEIGHT), BG)
        draw = ImageDraw.Draw(img)

        draw.text((4, 2), "> " + trunc, fill=PROMPT_COLOR, font=font)
        draw.line([(4, 14), (124, 14)], fill=DIM_GREEN, width=1)

        lines = wrap_text(partial, font, WIDTH - 10, draw)
        y = 20
        for line in lines:
            draw.text((5, y), line, fill=GREEN, font=font)
            y += 13
            if y > HEIGHT - 5:
                break

        # blinking cursor at end of text
        if chars_shown < total:
            bbox = draw.textbbox((0, 0), lines[-1] if lines else "", font=font)
            cx = 5 + bbox[2] - bbox[0] + 2
            cy_pos = y - 13
            draw.rectangle([(cx, cy_pos + 2), (cx + 6, cy_pos + 12)], fill=GREEN)

        disp.display(img)
        time.sleep(0.05)


def run_tlm(prompt):
    """run inference."""
    result = subprocess.run(
        ["python3", "tlm.py", prompt],
        capture_output=True, text=True, timeout=120,
        cwd="/home/walmart"
    )
    return result.stdout.strip()


def ask(disp, prompt):
    """full pipeline: prompt → thinking → inference → typing reveal."""
    # show the prompt
    show_prompt(disp, prompt)
    time.sleep(1)

    # start inference in background
    result = [None]
    def do_infer():
        result[0] = run_tlm(prompt)

    t = threading.Thread(target=do_infer)
    t.start()

    # animate thinking while waiting
    frame = 0
    while t.is_alive():
        show_thinking(disp, prompt, frame)
        frame += 1
        time.sleep(0.3)
    t.join()

    response = result[0] or "no response."
    print(f"Q: {prompt}")
    print(f"A: {response}")
    print()

    # typewriter reveal
    show_typing(disp, prompt, response)

    # hold final response
    show_response(disp, prompt, response)
    return response


def interactive():
    """interactive mode."""
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

    # clear on exit
    disp.display(Image.new("RGB", (WIDTH, HEIGHT), BG))


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] in ("-i", "--interactive"):
        interactive()
    elif len(sys.argv) > 1 and sys.argv[1] == "--boot":
        disp = get_display()
        show_boot(disp)
    elif len(sys.argv) > 1:
        disp = get_display()
        prompt = " ".join(sys.argv[1:])
        ask(disp, prompt)
    else:
        disp = get_display()
        show_boot(disp)
        print("tlm lcd ready. use -i for interactive or pass a question.")
