#!/usr/bin/python3
import sys
import tty
import termios
import csv
import math
import threading
import time
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

OVERLAY_DIR   = "construction"
N_IMAGES      = 15

TRUCK_PATH    = "construction/truck.png"
TRUCK_HEIGHT  = 75       # pixels tall on display
TRUCK_SPEED   = 1         # pixels per frame
TRUCK_FPS     = 30        # animation frames per second

FINAL_SENTINEL = "__FINAL__"

WHITE = (255, 255, 255)
BLACK = (0,   0,   0)

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


def assign_overlays(n_names, n_images):
    names_per_image = n_names // n_images
    no_image_count  = n_names - n_images * names_per_image
    assignments = [None] * no_image_count
    for img_idx in range(1, n_images + 1):
        assignments.extend([img_idx] * names_per_image)
    assignments.append(None)  # final slide
    return assignments


def fit_font_size(names, font_path, max_width, max_size=28, min_size=8):
    dummy = Image.new("RGB", (max_width, 10))
    draw  = ImageDraw.Draw(dummy)
    real_names = [n for n in names if n != FINAL_SENTINEL]
    for size in range(max_size, min_size - 1, -1):
        font = ImageFont.truetype(font_path, size)
        if all(draw.textbbox((0, 0), n, font=font)[2] <= max_width - 4 for n in real_names):
            return size
    return min_size


def get_line_height(font):
    dummy = Image.new("RGB", (256, 64))
    draw  = ImageDraw.Draw(dummy)
    bbox  = draw.textbbox((0, 0), TALL_REF, font=font)
    return bbox[3] - bbox[1]


def compute_y_positions(name_font_size, padding=10):
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


def load_overlay(path, width, height):
    overlay = Image.open(path).convert("RGBA").resize((width, height))
    r, g, b, a = overlay.split()
    return Image.merge("RGBA", (b, g, r, a))


def load_all_overlays(overlay_dir, n_images, width, height):
    overlays = {}
    for i in range(1, n_images + 1):
        path = f"{overlay_dir}/{i}.png"
        try:
            overlays[i] = load_overlay(path, width, height)
        except FileNotFoundError:
            print(f"Warning: overlay not found: {path}")
            overlays[i] = None
    return overlays


def load_truck(path, height):
    img = Image.open(path).convert("RGBA")
    ratio = img.width / img.height
    w = int(height * ratio)
    img = img.resize((w, height))
    r, g, b, a = img.split()
    return Image.merge("RGBA", (b, g, r, a))


def reorder_rows(arr):
    reordered = np.zeros_like(arr)
    reordered[0:32]   = arr[32:64]
    reordered[32:64]  = arr[0:32]
    reordered[64:96]  = arr[96:128]
    reordered[96:128] = arr[64:96]
    return reordered


def render_base_slide(name, name_font_size, y_positions, overlay=None):
    """Render slide without truck — cached per slide change."""
    if name == FINAL_SENTINEL:
        canvas = Image.new("RGB", (WIDTH, HEIGHT), BLACK)
        draw   = ImageDraw.Draw(canvas)
        font_lg = ImageFont.truetype(FONT_PATH,     28)
        font_sm = ImageFont.truetype(FONT_PATH_REG, 18)
        lines = [("Congrats", font_lg), ("Swarthmore Engineers!", font_sm)]
        padding = 12
        dummy_draw = ImageDraw.Draw(Image.new("RGB", (WIDTH, HEIGHT)))
        heights = [dummy_draw.textbbox((0, 0), t, font=f)[3] for t, f in lines]
        total_h = sum(heights) + padding * (len(heights) - 1)
        y = (HEIGHT - total_h) // 2
        for (text, font), h in zip(lines, heights):
            bbox = draw.textbbox((0, 0), text, font=font)
            w    = bbox[2] - bbox[0]
            x    = (WIDTH - w) // 2
            draw.text((x, y), text, font=font, fill=WHITE)
            y += h + padding
        return canvas

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

    if overlay is not None:
        canvas = canvas.convert("RGBA")
        canvas = Image.alpha_composite(canvas, overlay)
        canvas = canvas.convert("RGB")

    return canvas


def composite_truck(base_canvas, truck_img, truck_x):
    """Paste truck onto a copy of the base canvas at the given x position."""
    canvas = base_canvas.copy().convert("RGBA")
    y = HEIGHT - truck_img.height
    canvas.paste(truck_img, (truck_x, y), truck_img)
    return canvas.convert("RGB")


def finalize(img):
    arr = reorder_rows(np.asarray(img).copy())
    return np.ascontiguousarray(np.flipud(np.fliplr(arr))).copy()


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

    names.append(FINAL_SENTINEL)
    n_real = len(names) - 1
    print(f"Loaded {n_real} names + final slide.")

    # truck appears on second half of name slides
    truck_start_index = n_real // 2

    name_font_size = fit_font_size(names, FONT_PATH, WIDTH)
    print(f"Using font size {name_font_size} for names.")

    y_positions = compute_y_positions(name_font_size)
    assignments = assign_overlays(n_real, N_IMAGES)
    overlays    = load_all_overlays(OVERLAY_DIR, N_IMAGES, WIDTH, HEIGHT)
    truck_img   = load_truck(TRUCK_PATH, TRUCK_HEIGHT)

    no_img = assignments[:n_real].count(None)
    print(f"Overlay assignment: {no_img} names with no image, {n_real - no_img} with images.")
    print(f"Truck appears from slide {truck_start_index + 1} onward.")

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

    # shared state
    state = {
        "index":       0,
        "truck_x":     -truck_img.width,
        "base_canvas": None,
        "show_truck":  False,
        "running":     True,
    }
    lock = threading.Lock()

    def get_base(i):
        img_idx = assignments[i]
        overlay = overlays.get(img_idx) if img_idx is not None else None
        return render_base_slide(names[i], name_font_size, y_positions, overlay)

    # init
    state["base_canvas"] = get_base(0)
    state["show_truck"]  = (0 >= truck_start_index and names[0] != FINAL_SENTINEL)

    framebuffer = finalize(state["base_canvas"])

    matrix = piomatter.PioMatter(
        colorspace=piomatter.Colorspace.RGB888Packed,
        pinout=piomatter.Pinout.Active3,
        framebuffer=framebuffer,
        geometry=geometry,
    )
    matrix.show()

    def show(i):
        with lock:
            state["index"]       = i
            state["base_canvas"] = get_base(i)
            state["show_truck"]  = (i >= truck_start_index and names[i] != FINAL_SENTINEL)
            # state["truck_x"]     = -truck_img.width  # reset truck on slide change
        if names[i] == FINAL_SENTINEL:
            print(f"  [{i+1}/{len(names)}] *** Final slide ***")
        else:
            img_idx = assignments[i]
            tag = f"image {img_idx}" if img_idx is not None else "no image"
            truck_tag = " + truck" if i >= truck_start_index else ""
            print(f"  [{i+1}/{len(names)}] {names[i]} ({tag}{truck_tag})")

    def animation_loop():
        interval = 1.0 / TRUCK_FPS
        while state["running"]:
            with lock:
                if state["show_truck"]:
                    tx = state["truck_x"]
                    canvas = composite_truck(state["base_canvas"], truck_img, tx)
                    state["truck_x"] = tx + TRUCK_SPEED
                    if state["truck_x"] > WIDTH:
                        state["truck_x"] = -truck_img.width
                else:
                    canvas = state["base_canvas"]
                framebuffer[:] = finalize(canvas)
            matrix.show()
            time.sleep(interval)

    anim_thread = threading.Thread(target=animation_loop, daemon=True)
    anim_thread.start()

    show(0)

    fd  = sys.stdin.fileno()
    old = termios.tcgetattr(fd)

    index = 0

    try:
        tty.setraw(fd)
        while True:
            ch   = sys.stdin.read(1)
            code = ord(ch)

            if code == 27:
                seq = sys.stdin.read(2)

                if seq == '[6':
                    sys.stdin.read(1)
                    index = (index + 1) % len(names)
                    show(index)

                elif seq == '[5':
                    sys.stdin.read(1)
                    index = (index - 1) % len(names)
                    show(index)

                elif seq == '[C':
                    index = (index + 1) % len(names)
                    show(index)

                elif seq == '[D':
                    index = (index - 1) % len(names)
                    show(index)

            elif code == 46:
                index = 0
                show(index)

            elif code == 3:
                break

    finally:
        state["running"] = False
        termios.tcsetattr(fd, termios.TCSADRAIN, old)
        print("\nDone.")


if __name__ == "__main__":
    main()