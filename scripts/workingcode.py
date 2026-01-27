# SPDX-FileCopyrightText: 2022 Liz Clark for Adafruit Industries
#
# SPDX-License-Identifier: MIT

import os
import time
import ssl
import wifi
import socketpool
import microcontroller
import adafruit_requests
import digitalio
import board
from adafruit_character_lcd.character_lcd import Character_LCD_Mono
from SEPTA import queryRoute

# Define screen
lcd_columns = 16
lcd_rows    = 2

# Map pins based on wiring
rs = digitalio.DigitalInOut(board.GP15)  # Register Select
en = digitalio.DigitalInOut(board.GP14)  # Enable
d4 = digitalio.DigitalInOut(board.GP13)  # Data 4
d5 = digitalio.DigitalInOut(board.GP12)  # Data 5
d6 = digitalio.DigitalInOut(board.GP11)  # Data 6
d7 = digitalio.DigitalInOut(board.GP10)  # Data 7

# Set up LCD
lcd = Character_LCD_Mono(rs, en, d4, d5, d6, d7, lcd_columns, lcd_rows)

#  connect to SSID
wifi.radio.connect(os.getenv('CIRCUITPY_WIFI_SSID'), os.getenv('CIRCUITPY_WIFI_PASSWORD'))
pool = socketpool.SocketPool(wifi.radio)
requests = adafruit_requests.Session(pool, ssl.create_default_context())

while True:
    try:
        # Call function that pulls from SEPTA API
        display_this = queryRoute("Jefferson")
        # Display the result
        lcd.clear()
        lcd.message = display_this
        #  delays for 1 minute
        time.sleep(60)
        lcd.clear()
        lcd.message = "Refreshing .."
        time.sleep(3)
    # pylint: disable=broad-except
    except Exception as e:
        print("Error:\n", str(e))
        print("Resetting microcontroller in 10 seconds")
        time.sleep(10)
        microcontroller.reset()