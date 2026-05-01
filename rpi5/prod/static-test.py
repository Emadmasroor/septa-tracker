#!/usr/bin/python3
import numpy as np
import PIL.Image as Image
import PIL.ImageDraw as ImageDraw
import PIL.ImageFont as ImageFont
import adafruit_blinka_raspberry_pi5_piomatter as piomatter
from datetime import datetime
import time

WIDTH = 256
HEIGHT = 128
N_ADDR_LINES = 4
N_LANES = 4

FONT_PATH = "/usr/share/fonts/truetype/dejavu/DejaVuSansMono-Bold.ttf"
FONT_SMALL = 14
FONT_LARGE = 18

WHITE  = (255, 255, 255)
RED    = (0, 0, 255)
GREEN  = (0, 255, 0)
YELLOW = (0, 255, 255)
GRAY   = (180, 180, 180)
BLACK  = (0, 0, 0)

trains = [
    {"dest": "Temple University", "arrives": "4:32 PM", "delay": 0},
    {"dest": "Temple University", "arrives": "4:47 PM", "delay": 3},
    {"dest": "Temple University", "arrives": "5:01 PM", "delay": 0},
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

def render_frame(trains):
    canvas = Image.new("RGB", (WIDTH, HEIGHT), BLACK)
    draw = ImageDraw.Draw(canvas)
    font_lg = ImageFont.truetype(FONT_PATH, FONT_LARGE)
    font_sm = ImageFont.truetype(FONT_PATH, FONT_SMALL)

    now = datetime.now().strftime("%I:%M %p")
    tw = draw.textlength(now, font=font_sm)
    draw.text((WIDTH - tw - 2, 2), now, font=font_sm, fill=WHITE)
    draw.text((2, 2), "SEPTA", font=font_sm, fill=YELLOW)
    draw.line([(0, 20), (WIDTH, 20)], fill=GRAY, width=1)

    row_h = (HEIGHT - 22) // len(trains)
    for i, train in enumerate(trains):
        y = 22 + i * row_h
        color = GREEN if train["delay"] == 0 else RED
        draw.text((4, y), train["dest"], font=font_lg, fill=WHITE)
        draw.text((4, y + FONT_LARGE + 1), train["arrives"], font=font_sm, fill=color)
        if train["delay"] > 0:
            draw.text((94, y + FONT_LARGE + 1), f"+{train['delay']} min", font=font_sm, fill=RED)
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

try:
    while True:
        framebuffer[:] = render_frame(trains)
        matrix.show()
        time.sleep(30)
except KeyboardInterrupt:
    pass