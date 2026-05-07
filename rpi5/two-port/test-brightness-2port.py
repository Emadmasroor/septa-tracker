#!/usr/bin/python3
"""
Test script: solid color on all 16 panels (4-wide x 4-tall, 256x128)
using 4 lanes (2 ports x 2 lanes each) via Active3.
"""

import numpy as np
import PIL.Image as Image
import adafruit_blinka_raspberry_pi5_piomatter as piomatter
from adafruit_blinka_raspberry_pi5_piomatter.pixelmappers import simple_multilane_mapper

WIDTH = 256
HEIGHT = 128
N_LANES = 4
N_ADDR_LINES = 5

# Solid red test image
canvas = Image.new("RGB", (WIDTH, HEIGHT), (255,255, 255))
framebuffer = np.asarray(canvas) + 0  # mutable copy

pixelmap = simple_multilane_mapper(WIDTH, HEIGHT, N_ADDR_LINES, N_LANES)
geometry = piomatter.Geometry(
    width=WIDTH,
    height=HEIGHT,
    n_addr_lines=N_ADDR_LINES,
    map=pixelmap,
    n_lanes=N_LANES,
    n_planes=10,
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