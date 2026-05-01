#!/usr/bin/python3
"""
Display scrolling text on four 64x32 matrix panels (256x32 total).
Uses a bitmap font for crisp, fully-opaque characters.
"""

import numpy as np
import PIL.Image as Image
import PIL.ImageDraw as ImageDraw
import PIL.ImageFont as ImageFont
import adafruit_blinka_raspberry_pi5_piomatter as piomatter

# --- Config ---
TEXT = "Nick / Aurelien E90 Project"
DISPLAY_WIDTH = 256
DISPLAY_HEIGHT = 32
FONT_PATH = "/usr/share/fonts/truetype/dejavu/DejaVuSansMono-Bold.ttf"
FONT_SIZE = 12
TEXT_COLOR = (255, 255, 255)
BG_COLOR = (0, 0, 0)

# --- Font ---
font = ImageFont.truetype(FONT_PATH, FONT_SIZE)
_, _, text_width, text_height = font.getbbox(TEXT)
print(f"Text size: {text_width}x{text_height}px")

# --- Image ---
image = Image.new("RGB", (DISPLAY_WIDTH, DISPLAY_HEIGHT), color=BG_COLOR)
draw = ImageDraw.Draw(image)
draw.text((0, (DISPLAY_HEIGHT - text_height) // 2), TEXT, font=font, fill=TEXT_COLOR)

# --- Matrix ---
framebuffer = np.asarray(image)
geometry = piomatter.Geometry(
    width=DISPLAY_WIDTH,
    height=DISPLAY_HEIGHT,
    n_addr_lines=4,
    rotation=piomatter.Orientation.Normal,
)
matrix = piomatter.PioMatter(
    colorspace=piomatter.Colorspace.RGB888Packed,
    pinout=piomatter.Pinout.Active3,
    framebuffer=framebuffer,
    geometry=geometry
)

matrix.show()
input("Press Enter to exit...")
