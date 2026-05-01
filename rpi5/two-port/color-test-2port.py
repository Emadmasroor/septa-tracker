#!/usr/bin/python3
import numpy as np
import adafruit_blinka_raspberry_pi5_piomatter as piomatter

WIDTH = 256
HEIGHT = 128
N_ADDR_LINES = 4
N_LANES = 4
PANEL_W = 64
PANEL_H = 32

def make_matrixmap(width, height, n_addr_lines, serpentine, row_offset=0):
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

def combine_port_maps(m1, m2, pixels_across):
    result = []
    for addr in range(16):
        for x in range(pixels_across):
            idx = addr * pixels_across * 2 + x * 2
            result.append(m1[idx])
            result.append(m1[idx + 1])
            result.append(m2[idx])
            result.append(m2[idx + 1])
    return result

m_port1, pixels_across = make_matrixmap(WIDTH, 64, N_ADDR_LINES, serpentine=True, row_offset=0)
m_port2, _             = make_matrixmap(WIDTH, 64, N_ADDR_LINES, serpentine=True, row_offset=64)
pixelmap = combine_port_maps(m_port1, m_port2, pixels_across)

# Number each panel with a unique color AND draw the panel number in brightness
# Panel 0=top-left in canvas, panel 15=bottom-right
# Each panel gets a distinct hue, plus a small bright dot in top-left corner
# to indicate which canvas row/col it is
canvas = np.zeros((HEIGHT, WIDTH, 3), dtype=np.uint8)

# 16 distinct colors, one per panel
panel_colors = [
    (0,0,180),   # panel 0: dark red
    (0,180,0),   # panel 1: dark green  
    (180,0,0),   # panel 2: dark blue
    (0,180,180), # panel 3: dark yellow
    (180,0,180), # panel 4: dark cyan
    (180,90,0),  # panel 5: dark orange
    (90,0,180),  # panel 6: dark purple
    (180,180,0), # panel 7: light blue-green
    (0,0,255),   # panel 8: bright red
    (0,255,0),   # panel 9: bright green
    (255,0,0),   # panel 10: bright blue
    (0,255,255), # panel 11: bright yellow
    (255,0,255), # panel 12: bright cyan
    (255,200,0), # panel 13: bright orange-blue
    (100,0,255), # panel 14: bright purple
    (255,255,0), # panel 15: bright cyan-red
]

for i, color in enumerate(panel_colors):
    row = (i // 4) * PANEL_H
    col = (i % 4) * PANEL_W
    canvas[row:row+PANEL_H, col:col+PANEL_W] = color
    # bright white dot in top-left of each panel to show orientation
    canvas[row:row+4, col:col+4] = (255, 255, 255)

framebuffer = canvas.copy()

geometry = piomatter.Geometry(
    width=WIDTH,
    height=HEIGHT,
    n_addr_lines=N_ADDR_LINES,
    map=pixelmap,
    n_lanes=N_LANES,
    n_planes=2,
    n_temporal_planes=1,
)
matrix = piomatter.PioMatter(
    colorspace=piomatter.Colorspace.RGB888Packed,
    pinout=piomatter.Pinout.Active3,
    framebuffer=framebuffer,
    geometry=geometry,
)
matrix.show()
input("")