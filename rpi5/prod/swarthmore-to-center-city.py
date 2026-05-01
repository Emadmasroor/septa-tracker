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
N_LANES = 4

FONT_PATH = "/usr/share/fonts/truetype/dejavu/DejaVuSansMono-Bold.ttf"
LOGO_PATH = "/home/fetcar/septa-tracker/rpi5/septa.png"
FONT_SMALL = 14
FONT_LARGE = 18

WHITE  = (255, 255, 255)
RED    = (0, 0, 255)
GREEN  = (0, 255, 0)
YELLOW = (0, 255, 255)
GRAY   = (180, 180, 180)
BLACK  = (0, 0, 0)

def fetch_trains():
    try:
        url = "https://www3.septa.org/api/Arrivals/index.php?station=Swarthmore&results=20&direction=N"
        response = requests.get(url, timeout=10)
        data = response.json()

        trains = []
        for key, value in data.items():
            for entry_list in value:
                for entry in entry_list.get("Northbound", []):
                    line = entry.get("line", "")
                    if "Media" not in line and "Wawa" not in line:
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

        return trains if trains else fallback_trains()
    except Exception as e:
        print(f"API error: {e}")
        return fallback_trains()

def fallback_trains():
    return [
        {"dest": "No data", "arrives": "--:--", "delay": 0},
        {"dest": "No data", "arrives": "--:--", "delay": 0},
        {"dest": "No data", "arrives": "--:--", "delay": 0},
    ]

def build_map(width, height, n_addr_lines, serpentine, row_offset=0):
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
    result = []
    for addr in range(16):
        for x in range(pixels_across):
            idx = addr * pixels_across * 2 + x * 2
            result.append(m1[idx])
            result.append(m1[idx + 1])
            result.append(m2[idx])
            result.append(m2[idx + 1])
    return result

logo_raw = Image.open(LOGO_PATH).convert("RGB")
logo_h_crop = int(logo_raw.height * 0.68)
logo_raw = logo_raw.crop((0, 0, logo_raw.width, logo_h_crop))
logo_raw = logo_raw.crop((50, 50, logo_raw.width - 80, logo_raw.height))
logo_size = 16
ratio = logo_raw.width / logo_raw.height
logo_raw = logo_raw.resize((int(logo_size * ratio), logo_size), Image.LANCZOS)

logo_arr = np.array(logo_raw)

# Sample blue from top-right region and red from top-left region
blue = logo_arr[2, logo_arr.shape[1] - 3].tolist()
red = logo_arr[2, 2].tolist()
# print(f"sampled blue: {blue}, sampled red: {red}")

# Fix corners
logo_arr[0:2, 0:2] = red
logo_arr[-2:, 0:2] = red
logo_arr[0:2, -2:] = blue
logo_arr[-2:, -2:] = blue
logo_raw = Image.fromarray(logo_arr)

def render_frame(trains):
    canvas = Image.new("RGB", (WIDTH, HEIGHT), BLACK)
    draw = ImageDraw.Draw(canvas)
    font_lg = ImageFont.truetype(FONT_PATH, FONT_LARGE)
    font_sm = ImageFont.truetype(FONT_PATH, FONT_SMALL)

    # SEPTA text then logo to the right
    draw.text((2, 2), "SEPTA", font=font_sm, fill=YELLOW)
    text_w = int(draw.textlength("SEPTA", font=font_sm))
    canvas.paste(logo_raw, (text_w + 10, 2))

    # Time top-right
    now = datetime.now().strftime("%I:%M %p")
    tw = draw.textlength(now, font=font_sm)
    draw.text((WIDTH - tw - 3, 2), now, font=font_sm, fill=WHITE)

    draw.line([(0, 20), (WIDTH, 20)], fill=GRAY, width=1)

    row_h = (HEIGHT - 22) // len(trains)
    for i, train in enumerate(trains):
        y = 22 + i * row_h
        color = GREEN if train["delay"] == 0 else RED
        draw.text((2, y), train["dest"], font=font_lg, fill=WHITE)
        draw.text((2, y + FONT_LARGE + 1), train["arrives"], font=font_sm, fill=color)
        if train["delay"] > 0:
            draw.text((94, y + FONT_LARGE + 1), f"+{train['delay']}", font=font_sm, fill=RED)
        else:
            draw.text((94, y + FONT_LARGE + 1), "On time", font=font_sm, fill=GREEN)

    arr = np.asarray(canvas).copy()
    reordered = np.zeros_like(arr)
    reordered[0:32]   = arr[32:64]
    reordered[32:64]  = arr[0:32]
    reordered[64:96]  = arr[96:128]
    reordered[96:128] = arr[64:96]

    return np.ascontiguousarray(np.flipud(np.fliplr(reordered))).copy()

# Build pixel map
m1, pixels_across = build_map(WIDTH, 64, N_ADDR_LINES, serpentine=True, row_offset=64)
m2, _             = build_map(WIDTH, 64, N_ADDR_LINES, serpentine=True, row_offset=0)
pixelmap = combine_maps(m2, m1, pixels_across)

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