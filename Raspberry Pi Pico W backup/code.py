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

lcd = Character_LCD_Mono(rs, en, d4, d5, d6, d7, lcd_columns, lcd_rows)
# lcd.message = "Hello, World"

#  SEPTA API pull
SEPTA_url = "https://www3.septa.org/api/Arrivals/index.php?station=Swarthmore&results=1&direction=N"

#  connect to SSID
network_name = "SwatDevice"     # received from
network_pass = "DeviceSecure"   # Swarthmore IT

# Global delay (this is how long to wait between pings)
wait_time = 10
reset_time = 60*60

# Cycle delay (this is how long each element of the cycle waits
hiccup = 0.5

# Some code that helps pull from API
pool = socketpool.SocketPool(wifi.radio)
requests = adafruit_requests.Session(pool, ssl.create_default_context())

def querySEPTA(num):
    # Limited functionality. Only Swarthmore to Philly.
    disp_string     = ""
    results = []
    origin_station  = "Swarthmore"
    direction       = "N"
    direc           = "Northbound"
    destination     = "PHILA"
    URL_API= f"https://www3.septa.org/api/NextToArrive/index.php?req1={origin_station}&req2=Market%20East&req3={num}"
    response = requests.get(URL_API)
    data = response.json()
    for entry in data:
        scheduled   = entry["orig_departure_time"]
        status      = entry["orig_delay"]
        result      = f"{scheduled} {status}\n"
        results.append(result)
        disp_string += result
    # close out
    response.close()
    return disp_string


start_time = time.monotonic()
while True:

    while not wifi.radio.connected:
        print("Wifi not connected! Connecting ...")
        wifi.radio.connect(network_name,network_pass)
        lcd.message = f"Connecting to \n{network_name}"
        for i in range(5):
            time.sleep(wait_time/5)
            lcd.message += "."

    try:
        mes = querySEPTA(2) # pull two most recent messages
        lcd.clear()
        lcd.message = mes
        print("Printing message to LCD")
        print("Going to sleep!")
        time.sleep(wait_time)
        lcd.clear()
        lcd.message = f"Refresh {wait_time} sec\n"
        for i in range(8):
            time.sleep(hiccup/8)
            lcd.message += "."
    # pylint: disable=broad-except
    except Exception as e:
        print("some error occured!")
        print(e)
        lcd.message = f"{e[0:lcd_columns]}\n{e[lcd_columns:2*lcd_columns]}"
        # microcontroller.reset()
        time.sleep(3*hiccup)

    lcd.clear()
    lcd.message = "Trains to PHILA\n"
    if wifi.radio.connected:
        print("Still connected")
        lcd.message += f"cnctd {network_name}"
        time.sleep(6*hiccup)
    else:
        print("Disconnected!")
        lcd.message += f"Disconnected!"
        time.sleep(10*hiccup)

    current_time = time.monotonic()-start_time
    print(f"The current time is {current_time}")
    if current_time > reset_time:
        microcontroller.reset()
