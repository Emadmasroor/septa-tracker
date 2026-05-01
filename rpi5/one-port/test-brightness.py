#!/usr/bin/python3
import numpy as np
import PIL.Image as Image
import adafruit_blinka_raspberry_pi5_piomatter as piomatter

DISPLAY_WIDTH = 128
DISPLAY_HEIGHT = 64

image = Image.new("RGB", (DISPLAY_WIDTH, DISPLAY_HEIGHT), color=(255, 255, 255))
framebuffer = np.asarray(image)

geometry = piomatter.Geometry(
    width=DISPLAY_WIDTH,
    height=DISPLAY_HEIGHT,
    n_addr_lines=5,
    rotation=piomatter.Orientation.Normal,
)

matrix = piomatter.PioMatter(
    colorspace=piomatter.Colorspace.RGB888Packed,
    pinout=piomatter.Pinout.Active3,
    framebuffer=framebuffer,
    geometry=geometry,
)

matrix.show()
input("Press Enter to exit...")