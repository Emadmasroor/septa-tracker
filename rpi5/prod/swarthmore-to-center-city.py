#!/usr/bin/python3
import numpy as np
import PIL.Image as Image
import PIL.ImageDraw as ImageDraw
import PIL.ImageFont as ImageFont
import adafruit_blinka_raspberry_pi5_piomatter as piomatter
from datetime import datetime
import time
import requests

WIDTH = 256
HEIGHT = 128
N_ADDR_LINES = 4
N_LANES = 4  # 2 HUB75 ports x 2 lanes each

FONT_PATH = "/usr/share/fonts/truetype/dejavu/DejaVuSansMono-Bold.ttf"
SEPTA_LOGO_PATH = "/home/fetcar/septa-tracker/rpi5/septa.png"
FONT_SMALL  = 14
FONT_MEDIUM = 16
FONT_LARGE  = 18

# Colors are BGR due to Active3 pinout
WHITE  = (255, 255, 255)
RED    = (0, 0, 255)
ORANGE = (0, 128, 255)
GREEN  = (0, 255, 0)
YELLOW = (0, 255, 255)
GRAY   = (180, 180, 180)
GARNET = (0, 0, 139)
BLACK  = (0, 0, 0)


def fetch_trains():
    try:
        url = "https://www3.septa.org/api/Arrivals/index.php?station=Swarthmore&results=20&direction=N"
        response = requests.get(url, timeout=10)
        data = response.json()

        trains = []
        for key, value in data.items():
            if not isinstance(value, list):
                continue
            for entry_list in value:
                if not isinstance(entry_list, dict):
                    continue
                for entry in entry_list.get("Northbound", []):
                    line   = entry.get("line") or ""
                    origin = entry.get("origin") or ""
                    if "Media" not in line and "Wawa" not in line and \
                       "Media" not in origin and "Wawa" not in origin:
                        continue

                    sched = entry["sched_time"][11:16]
                    hour, minute = int(sched[:2]), int(sched[3:])
                    ampm = "AM" if hour < 12 else "PM"
                    hour12 = hour % 12 or 12
                    arrives = f"{hour12}:{minute:02d} {ampm}"

                    status = entry["status"]
                    if status == "On Time":
                        delay = 0
                    else:
                        try:
                            delay = int(status.split()[0])
                        except:
                            delay = 0

                    trains.append({"dest": entry["destination"], "arrives": arrives, "delay": delay})
                    if len(trains) == 3:
                        return trains

        return trains if trains else no_trains()
    except Exception as e:
        print(f"API error: {e}")
        return no_trains()


def no_trains():
    return [
        {"dest": "No trains", "arrives": "tonight", "delay": 0},
        {"dest": "",          "arrives": "",         "delay": 0},
        {"dest": "",          "arrives": "",         "delay": 0},
    ]


def build_map(width, height, n_addr_lines, serpentine, row_offset=0):
    # Replicates piomatter's internal make_matrixmap logic for a single port.
    # row_offset shifts the map into the correct region of the full framebuffer.
    panel_height = 2 << n_addr_lines
    half_panel_height = 1 << n_addr_lines
    v_panels = height // panel_height
    pixels_across = width * v_panels
    result = []
    for i in range(half_panel_height):
        for j in range(pixels_across):
            panel_no = j // width
            panel_idx = j % width
            if serpentine and panel_no % 2:
                x = width - panel_idx - 1
                y0 = (panel_no + 1) * panel_height - i - 1
                y1 = (panel_no + 1) * panel_height - i - half_panel_height - 1
            else:
                x = panel_idx
                y0 = panel_no * panel_height + i
                y1 = panel_no * panel_height + i + half_panel_height
            result.append(x + width * (y0 + row_offset))
            result.append(x + width * (y1 + row_offset))
    return result, pixels_across


def combine_maps(m1, m2, pixels_across):
    # Interleave two port maps at the lane level so piomatter's render loop
    # sees (port1_lane0, port1_lane1, port2_lane0, port2_lane1) per pixel.
    result = []
    for addr in range(16):
        for x in range(pixels_across):
            idx = addr * pixels_across * 2 + x * 2
            result.append(m1[idx])
            result.append(m1[idx + 1])
            result.append(m2[idx])
            result.append(m2[idx + 1])
    return result


def load_septa_logo(path, size=16):
    img = Image.open(path).convert("RGB")
    # Crop bottom ~32% which contains the "SEPTA" text wordmark
    img = img.crop((0, 0, img.width, int(img.height * 0.68)))
    # Crop white border around the rounded rectangle
    img = img.crop((50, 50, img.width - 80, img.height))
    ratio = img.width / img.height
    img = img.resize((int(size * ratio), size), Image.LANCZOS)

    arr = np.array(img)
    arr = arr[:, :, ::-1]  # swap RGB to BGR
    # Sample true blue/red from inside the logo to fix LANCZOS corner artifacts
    blue = arr[2, arr.shape[1] - 3].tolist()
    red  = arr[2, 2].tolist()
    arr[0:2,  0:2]  = red
    arr[-2:,  0:2]  = red
    arr[0:2,  -2:]  = blue
    arr[-2:,  -2:]  = blue
    return Image.fromarray(arr)


def reorder_rows(arr):
    # Panels are physically wired so that within each port, the two panel rows
    # are swapped relative to the framebuffer scan order.
    reordered = np.zeros_like(arr)
    reordered[0:32]   = arr[32:64]
    reordered[32:64]  = arr[0:32]
    reordered[64:96]  = arr[96:128]
    reordered[96:128] = arr[64:96]
    return reordered


def wait_for_network(timeout=60):
    import socket
    print("Waiting for network...")
    start = time.time()
    while time.time() - start < timeout:
        try:
            socket.create_connection(("www3.septa.org", 80), timeout=5)
            print("Network ready.")
            return True
        except OSError:
            time.sleep(3)
    print("Network timeout, starting with fallback data.")
    return False


septa_logo = load_septa_logo(SEPTA_LOGO_PATH)


def render_frame(trains):
    canvas = Image.new("RGB", (WIDTH, HEIGHT), BLACK)
    draw = ImageDraw.Draw(canvas)
    font_lg = ImageFont.truetype(FONT_PATH, FONT_LARGE)
    font_md = ImageFont.truetype(FONT_PATH, FONT_MEDIUM)
    font_sm = ImageFont.truetype(FONT_PATH, FONT_SMALL)

    # Header: SEPTA label, SEPTA logo, SWAT ENGR text, and current time
    draw.text((3, 2), "[MED]", font=font_sm, fill=YELLOW)
    text_w = int(draw.textlength("[MED]", font=font_sm))
    canvas.paste(septa_logo, (text_w + 10, 2))
    swat_x = text_w + 10 + septa_logo.width + 6
    draw.text((swat_x, 1), "SWAT ENGR", font=font_md, fill=GARNET)
    now = datetime.now().strftime("%I:%M %p")
    tw = int(draw.textlength(now, font=font_sm))
    draw.text((WIDTH - tw - 3, 2), now, font=font_sm, fill=WHITE)
    draw.line([(0, 20), (WIDTH, 20)], fill=GRAY, width=1)

    # Train rows
    row_h = (HEIGHT - 22) // len(trains)
    for i, train in enumerate(trains):
        y = 22 + i * row_h
        if train["delay"] == 0:
            color = GREEN
        elif train["delay"] < 6:
            color = ORANGE
        else:
            color = RED
        draw.text((2, y), train["dest"], font=font_lg, fill=WHITE)
        draw.text((2, y + FONT_LARGE + 1), train["arrives"], font=font_sm, fill=color)
        if train["delay"] > 0:
            delay_color = ORANGE if train["delay"] < 6 else RED
            draw.text((94, y + FONT_LARGE + 1), f"+{train['delay']}", font=font_sm, fill=delay_color)
        else:
            if train["arrives"]:
                draw.text((94, y + FONT_LARGE + 1), "On time", font=font_sm, fill=GREEN)

    arr = reorder_rows(np.asarray(canvas).copy())
    return np.ascontiguousarray(np.flipud(np.fliplr(arr))).copy()


# Build pixel map for two-port 4x4 panel grid.
# Port 1 (bottom 4x2) maps to fb rows 64-127, port 2 (top 4x2) to rows 0-63.
m1, pixels_across = build_map(WIDTH, 64, N_ADDR_LINES, serpentine=True, row_offset=64)
m2, _             = build_map(WIDTH, 64, N_ADDR_LINES, serpentine=True, row_offset=0)
pixelmap = combine_maps(m2, m1, pixels_across)

wait_for_network()
trains = fetch_trains()
framebuffer = render_frame(trains)

geometry = piomatter.Geometry(
    width=WIDTH,
    height=HEIGHT,
    n_addr_lines=N_ADDR_LINES,
    map=pixelmap,
    n_lanes=N_LANES,
    n_planes=4,
    n_temporal_planes=2,
)
matrix = piomatter.PioMatter(
    colorspace=piomatter.Colorspace.RGB888Packed,
    pinout=piomatter.Pinout.Active3,
    framebuffer=framebuffer,
    geometry=geometry,
)

last_fetch = 0
try:
    while True:
        now = time.time()
        if now - last_fetch > 60:
            trains = fetch_trains()
            last_fetch = now
        framebuffer[:] = render_frame(trains)
        matrix.show()
        time.sleep(30)
except KeyboardInterrupt:
    pass