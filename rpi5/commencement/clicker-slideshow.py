#!/usr/bin/python3
import sys
import tty
import termios
import csv
import numpy as np
import PIL.Image as Image
import PIL.ImageDraw as ImageDraw
import PIL.ImageFont as ImageFont
import adafruit_blinka_raspberry_pi5_piomatter as piomatter

WIDTH        = 256
HEIGHT       = 128
N_ADDR_LINES = 4
N_LANES      = 4

FONT_PATH     = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
FONT_PATH_REG = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"

WHITE = (255, 255, 255)
BLACK = (0,   0,   0)

# Reference string with tall characters to get stable line heights
TALL_REF = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz"


def load_names(path):
    names = []
    with open(path, newline='') as f:
        reader = csv.DictReader(f)
        for row in reader:
            first = row['First Name'].strip()
            last  = row['Last Name'].strip()
            names.append(f"{first} {last}")
    return names


def fit_font_size(names, font_path, max_width, max_size=28, min_size=8):
    dummy = Image.new("RGB", (max_width, 10))
    draw  = ImageDraw.Draw(dummy)
    for size in range(max_size, min_size - 1, -1):
        font = ImageFont.truetype(font_path, size)
        if all(draw.textbbox((0, 0), n, font=font)[2] <= max_width - 4 for n in names):
            return size
    return min_size


def get_line_height(font):
    """Return a stable line height using a tall reference string."""
    dummy = Image.new("RGB", (256, 64))
    draw  = ImageDraw.Draw(dummy)
    bbox  = draw.textbbox((0, 0), TALL_REF, font=font)
    return bbox[3] - bbox[1]


def reorder_rows(arr):
    reordered = np.zeros_like(arr)
    reordered[0:32]   = arr[32:64]
    reordered[32:64]  = arr[0:32]
    reordered[64:96]  = arr[96:128]
    reordered[96:128] = arr[64:96]
    return reordered


def render_slide(name, name_font_size, y_positions):
    """y_positions is a precomputed list of y coords for each line, stable across all names."""
    canvas = Image.new("RGB", (WIDTH, HEIGHT), BLACK)
    draw   = ImageDraw.Draw(canvas)

    font_congrats = ImageFont.truetype(FONT_PATH,     22)
    font_name     = ImageFont.truetype(FONT_PATH,     name_font_size)
    font_class    = ImageFont.truetype(FONT_PATH_REG, 16)

    lines = [
        ("Congratulations",             font_congrats),
        (name,                          font_name),
        ("Swarthmore Engineering 2026", font_class),
    ]

    for (text, font), y in zip(lines, y_positions):
        bbox = draw.textbbox((0, 0), text, font=font)
        w    = bbox[2] - bbox[0]
        x    = (WIDTH - w) // 2
        draw.text((x, y), text, font=font, fill=WHITE)

    arr = reorder_rows(np.asarray(canvas).copy())
    return np.ascontiguousarray(np.flipud(np.fliplr(arr))).copy()


def compute_y_positions(name_font_size, padding=10):
    """Compute stable y positions using reference string heights, not per-name heights."""
    font_congrats = ImageFont.truetype(FONT_PATH,     22)
    font_name     = ImageFont.truetype(FONT_PATH,     name_font_size)
    font_class    = ImageFont.truetype(FONT_PATH_REG, 16)

    heights = [
        get_line_height(font_congrats),
        get_line_height(font_name),
        get_line_height(font_class),
    ]

    total_h = sum(heights) + padding * (len(heights) - 1)
    y_start = (HEIGHT - total_h) // 2

    y_positions = []
    y = y_start
    for h in heights:
        y_positions.append(y)
        y += h + padding

    return y_positions


def build_map(width, height, n_addr_lines, serpentine, row_offset=0):
    panel_height      = 2 << n_addr_lines
    half_panel_height = 1 << n_addr_lines
    v_panels          = height // panel_height
    pixels_across     = width * v_panels
    result = []
    for i in range(half_panel_height):
        for j in range(pixels_across):
            panel_no  = j // width
            panel_idx = j % width
            if serpentine and panel_no % 2:
                x  = width - panel_idx - 1
                y0 = (panel_no + 1) * panel_height - i - 1
                y1 = (panel_no + 1) * panel_height - i - half_panel_height - 1
            else:
                x  = panel_idx
                y0 = panel_no * panel_height + i
                y1 = panel_no * panel_height + i + half_panel_height
            result.append(x + width * (y0 + row_offset))
            result.append(x + width * (y1 + row_offset))
    return result, pixels_across


def combine_maps(m1, m2, pixels_across):
    result = []
    for addr in range(16):
        for x in range(pixels_across):
            idx = addr * pixels_across * 2 + x * 2
            result.append(m1[idx])
            result.append(m1[idx + 1])
            result.append(m2[idx])
            result.append(m2[idx + 1])
    return result


def main():
    names = load_names("names.csv")
    if not names:
        print("No names found in names.csv")
        sys.exit(1)
    print(f"Loaded {len(names)} names.")

    name_font_size = fit_font_size(names, FONT_PATH, WIDTH)
    print(f"Using font size {name_font_size} for names.")

    y_positions = compute_y_positions(name_font_size)

    m1, pixels_across = build_map(WIDTH, 64, N_ADDR_LINES, serpentine=True, row_offset=64)
    m2, _             = build_map(WIDTH, 64, N_ADDR_LINES, serpentine=True, row_offset=0)
    pixelmap          = combine_maps(m2, m1, pixels_across)

    geometry = piomatter.Geometry(
        width=WIDTH,
        height=HEIGHT,
        n_addr_lines=N_ADDR_LINES,
        map=pixelmap,
        n_lanes=N_LANES,
        n_planes=4,
        n_temporal_planes=2,
    )

    index       = 0
    framebuffer = render_slide(names[index], name_font_size, y_positions)

    matrix = piomatter.PioMatter(
        colorspace=piomatter.Colorspace.RGB888Packed,
        pinout=piomatter.Pinout.Active3,
        framebuffer=framebuffer,
        geometry=geometry,
    )
    matrix.show()

    def show(i):
        framebuffer[:] = render_slide(names[i], name_font_size, y_positions)
        matrix.show()
        print(f"  [{i+1}/{len(names)}] {names[i]}")

    print("Use clicker to navigate. Ctrl+C to quit.\n")

    fd  = sys.stdin.fileno()
    old = termios.tcgetattr(fd)

    try:
        tty.setraw(fd)
        while True:
            ch   = sys.stdin.read(1)
            code = ord(ch)

            if code == 27:
                seq = sys.stdin.read(2)

                if seq == '[6':       # Page Down → NEXT
                    sys.stdin.read(1)
                    index = (index + 1) % len(names)
                    show(index)

                elif seq == '[5':     # Page Up → PREV
                    sys.stdin.read(1)
                    index = (index - 1) % len(names)
                    show(index)

                elif seq == '[C':     # Right arrow → NEXT
                    index = (index + 1) % len(names)
                    show(index)

                elif seq == '[D':     # Left arrow → PREV
                    index = (index - 1) % len(names)
                    show(index)

            elif code == 46:          # HOME button → first name
                index = 0
                show(index)

            elif code == 3:           # Ctrl+C
                break

    finally:
        termios.tcsetattr(fd, termios.TCSADRAIN, old)
        print("\nDone.")


if __name__ == "__main__":
    main()