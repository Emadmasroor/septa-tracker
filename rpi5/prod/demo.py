#!/usr/bin/python3
import numpy as np
import PIL.Image as Image
import PIL.ImageDraw as ImageDraw
import PIL.ImageFont as ImageFont
import adafruit_blinka_raspberry_pi5_piomatter as piomatter
from datetime import datetime
import threading
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

SEPTA_SCREEN_DURATION    = 60  # seconds
CONGRATS_SCREEN_DURATION = 10  # seconds


def fetch_trains_northbound():
    try:
        url = "https://www3.septa.org/api/Arrivals/index.php?station=Swarthmore&results=20&direction=N"
        response = requests.get(url, timeout=10)
        return parse_trains(response.json(), "Northbound", 1)
    except Exception as e:
        print(f"API error (N): {e}")
        return no_trains()


def fetch_trains_southbound():
    try:
        url = "https://www3.septa.org/api/Arrivals/index.php?station=Swarthmore&results=20&direction=S"
        response = requests.get(url, timeout=10)
        return parse_trains(response.json(), "Southbound", 1)
    except Exception as e:
        print(f"API error (S): {e}")
        return no_trains()


def parse_trains(data, direction_key, count=1):
    trains = []
    now = datetime.now()
    for key, value in data.items():
        if not isinstance(value, list):
            continue
        for entry_list in value:
            if not isinstance(entry_list, dict):
                continue
            for entry in entry_list.get(direction_key, []):
                dest   = entry.get("destination") or ""
                line   = entry.get("line") or ""
                origin = entry.get("origin") or ""

                if direction_key == "Southbound":
                    # Accept any train terminating at Wawa or Media
                    if "Wawa" not in dest and "Media" not in dest:
                        continue
                else:
                    # Accept Media/Wawa line trains by line or origin
                    if "Media" not in line and "Wawa" not in line and \
                       "Media" not in origin and "Wawa" not in origin:
                        continue

                # Skip trains that have already departed
                try:
                    sched_dt = datetime.strptime(entry["sched_time"], "%Y-%m-%d %H:%M:%S.%f")
                    if sched_dt < now:
                        continue
                except:
                    pass

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

                trains.append({"dest": dest, "arrives": arrives, "delay": delay})
                if len(trains) == count:
                    return trains

    return trains if trains else no_trains()


def no_trains():
    return [{"dest": "No trains", "arrives": "tonight", "delay": 0}]


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


def draw_train_row(draw, y, train, font_lg, font_sm):
    if train["delay"] == 0:
        color = GREEN
    elif train["delay"] < 6:
        color = ORANGE
    else:
        color = RED
    draw.text((2, y), train["dest"], font=font_lg, fill=WHITE)
    draw.text((2, y + FONT_LARGE + 2), train["arrives"], font=font_sm, fill=color)
    if train["delay"] > 0:
        delay_color = ORANGE if train["delay"] < 6 else RED
        draw.text((100, y + FONT_LARGE + 2), f"+{train['delay']}", font=font_sm, fill=delay_color)
    elif train["arrives"] != "tonight":
        draw.text((100, y + FONT_LARGE + 2), "On time", font=font_sm, fill=GREEN)


def render_septa(northbound, southbound):
    canvas = Image.new("RGB", (WIDTH, HEIGHT), BLACK)
    draw = ImageDraw.Draw(canvas)
    font_lg = ImageFont.truetype(FONT_PATH, FONT_LARGE)
    font_md = ImageFont.truetype(FONT_PATH, FONT_MEDIUM)
    font_sm = ImageFont.truetype(FONT_PATH, FONT_SMALL)

    # Header
    draw.text((3, 2), "[MED]", font=font_sm, fill=YELLOW)
    text_w = int(draw.textlength("[MED]", font=font_sm))
    canvas.paste(septa_logo, (text_w + 10, 2))
    swat_x = text_w + 10 + septa_logo.width + 6
    draw.text((swat_x, 1), "SWAT ENGR", font=font_md, fill=GARNET)
    now = datetime.now().strftime("%I:%M %p")
    tw = int(draw.textlength(now, font=font_sm))
    draw.text((WIDTH - tw - 3, 2), now, font=font_sm, fill=WHITE)
    draw.line([(0, 20), (WIDTH, 20)], fill=GRAY, width=1)

    # Northbound
    draw.text((2, 23), "TO CENTER CITY", font=font_sm, fill=YELLOW)
    draw_train_row(draw, 38, northbound[0], font_lg, font_sm)

    draw.line([(0, 74), (WIDTH, 74)], fill=GRAY, width=1)

    # Southbound
    draw.text((2, 77), "TO MEDIA/WAWA", font=font_sm, fill=YELLOW)
    draw_train_row(draw, 92, southbound[0], font_lg, font_sm)

    arr = reorder_rows(np.asarray(canvas).copy())
    return np.ascontiguousarray(np.flipud(np.fliplr(arr))).copy()


def render_congrats():
    canvas = Image.new("RGB", (WIDTH, HEIGHT), BLACK)
    draw = ImageDraw.Draw(canvas)
    font_lg = ImageFont.truetype(FONT_PATH, FONT_LARGE)

    lines = ["Congrats", "Engineering", "Seniors!"]
    total_h = len(lines) * (FONT_LARGE + 6)
    y = (HEIGHT - total_h) // 2
    for line in lines:
        tw = int(draw.textlength(line, font=font_lg))
        draw.text(((WIDTH - tw) // 2, y), line, font=font_lg, fill=WHITE)
        y += FONT_LARGE + 6

    arr = reorder_rows(np.asarray(canvas).copy())
    return np.ascontiguousarray(np.flipud(np.fliplr(arr))).copy()


septa_logo = load_septa_logo(SEPTA_LOGO_PATH)

# Build pixel map for two-port 4x4 panel grid.
# Port 1 (bottom 4x2) maps to fb rows 64-127, port 2 (top 4x2) to rows 0-63.
m1, pixels_across = build_map(WIDTH, 64, N_ADDR_LINES, serpentine=True, row_offset=64)
m2, _             = build_map(WIDTH, 64, N_ADDR_LINES, serpentine=True, row_offset=0)
pixelmap = combine_maps(m2, m1, pixels_across)

wait_for_network()

fetch_state = {
    "northbound": fetch_trains_northbound(),
    "southbound": fetch_trains_southbound(),
    "fetching": False,
}


def fetch_in_background():
    fetch_state["fetching"] = True
    fetch_state["northbound"] = fetch_trains_northbound()
    fetch_state["southbound"] = fetch_trains_southbound()
    fetch_state["fetching"] = False


framebuffer = render_septa(fetch_state["northbound"], fetch_state["southbound"])

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
last_screen_switch = time.time()
showing_congrats = False

try:
    while True:
        now = time.time()

        # Fetch train data in background every 60s
        if now - last_fetch > 60 and not fetch_state["fetching"]:
            threading.Thread(target=fetch_in_background, daemon=True).start()
            last_fetch = now

        # Switch screens on schedule
        if showing_congrats and now - last_screen_switch > CONGRATS_SCREEN_DURATION:
            showing_congrats = False
            last_screen_switch = now
        elif not showing_congrats and now - last_screen_switch > SEPTA_SCREEN_DURATION:
            showing_congrats = True
            last_screen_switch = now

        if showing_congrats:
            framebuffer[:] = render_congrats()
        else:
            framebuffer[:] = render_septa(fetch_state["northbound"], fetch_state["southbound"])

        matrix.show()
        time.sleep(1)
except KeyboardInterrupt:
    pass