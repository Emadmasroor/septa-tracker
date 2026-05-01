#!/usr/bin/python3
import numpy as np
import PIL.Image as Image
import PIL.ImageDraw as ImageDraw
import PIL.ImageFont as ImageFont
import adafruit_blinka_raspberry_pi5_piomatter as piomatter
from adafruit_blinka_raspberry_pi5_piomatter.pixelmappers import simple_multilane_mapper

TEXT = "Nick / Aurelien E90 Project"
WIDTH = 256
HEIGHT = 128
N_LANES = 4
N_ADDR_LINES = 5
FONT_PATH = "/usr/share/fonts/truetype/dejavu/DejaVuSansMono-Bold.ttf"
FONT_SIZE = 24
TEXT_COLOR = (255, 255, 255)
BG_COLOR = (0, 0, 0)

font = ImageFont.truetype(FONT_PATH, FONT_SIZE)
_, _, text_width, text_height = font.getbbox(TEXT)

canvas = Image.new("RGB", (WIDTH, HEIGHT), BG_COLOR)
draw = ImageDraw.Draw(canvas)
draw.text((0, (HEIGHT - text_height) // 2), TEXT, font=font, fill=TEXT_COLOR)

framebuffer = np.asarray(canvas).copy()

pixelmap = simple_multilane_mapper(WIDTH, HEIGHT, N_ADDR_LINES, N_LANES)
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

matrix.show()
input("Press Enter to exit...")
