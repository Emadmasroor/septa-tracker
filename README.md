## E90 Project: High-Fidelity Swarthmore SEPTA Station Display

There is currently no way to monitor SEPTA arrival times at stations outside Philadelphia city limits, particularly in suburban Delaware County. This repository contains all code required by a Raspberry Pi Pico microcontroller to pull data from SEPTA and display to an LCD.

This project was created by Nick Fettig '26 and Aurelien Carretta '26 under the supervision of Professor Emad Masroor.

### Septa tracker local testing spin-up

- Run `chmod +x setup.sh`
- Run `setup.sh` to create virtual environment and install necessary dependencies.
- Run `source septa_venv/bin/activate` to active venv

### Septa tracker for display on USB (On RPI Pico 2)

- Run `screen /dev/tty.usbmodem* 115200` in terminal to forward logs to computer via usb
- To copy files from RPI to here use `cp /volumes/CIRCUITPY ./<folder>`
- To copy a backup here to RPI use:
  `cp -r ./<folder> /Volumes/CIRCUITPY`
