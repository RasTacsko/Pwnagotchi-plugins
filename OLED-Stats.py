import os
import time
import logging
from PIL import Image, ImageDraw, ImageFont
from pwnagotchi.ui.hw.libs.i2coled.epd import EPD
import subprocess
import pwnagotchi.plugins as plugins

class OLEDStats(plugins.Plugin):
    __author__ = 'https://github.com/RasTacsko'
    __version__ = '0.1.0'
    __license__ = 'GPL3'

    def __init__(self):
        self.I2C1 = 0x3C
        self.WIDTH = 128
        self.HEIGHT = 64
        self.FONTSIZE = 16
        self.LOOPTIME = 1.0

        # Get the directory of this script
        self.plugin_dir = os.path.dirname(os.path.realpath(__file__))

        # Initialize OLED display
        self.oled1 = EPD(address=self.I2C1, width=self.WIDTH, height=self.HEIGHT)
        self.oled1.Init()
        self.oled1.Clear()

        # Create blank image for drawing
        self.width = self.oled1.width
        self.height = self.oled1.height
        self.image = Image.new('1', (self.width, self.height))

        # Get drawing object
        self.draw = ImageDraw.Draw(self.image)

        # Load fonts using absolute paths
        font_path = os.path.join(self.plugin_dir, 'PixelOperator.ttf')
        icon_font_path = os.path.join(self.plugin_dir, 'lineawesome-webfont.ttf')

        self.font = ImageFont.truetype(font_path, 16)
        self.icon_font = ImageFont.truetype(icon_font_path, 18)

    def on_ui_update(self, ui):
        # Clear the image
        self.draw.rectangle((0, 0, self.width, self.height), outline=0, fill=0)

        # System monitoring commands
        IP = subprocess.check_output("hostname -I | cut -d' ' -f1 | head --bytes -1", shell=True)
        CPU = subprocess.check_output("top -bn1 | grep load | awk '{printf \"%.2fLA\", $(NF-2)}'", shell=True)
        MemUsage = subprocess.check_output("free -m | awk 'NR==2{printf \"%.2f%%\", $3*100/$2 }'", shell=True)
        Disk = subprocess.check_output("df -h | awk '$NF==\"/\"{printf \"%d/%dGB\", $3,$2}'", shell=True)
        Temperature = subprocess.check_output("vcgencmd measure_temp | cut -d '=' -f 2 | head --bytes -1", shell=True)

        # Draw icons and stats
        self.draw.text((0, 5), chr(62171), font=self.icon_font, fill=255)  # CPU icon
        self.draw.text((65, 5), chr(62609), font=self.icon_font, fill=255)  # Temperature icon
        self.draw.text((0, 25), chr(62776), font=self.icon_font, fill=255)  # Memory icon
        self.draw.text((65, 25), chr(63426), font=self.icon_font, fill=255)  # Disk icon
        self.draw.text((0, 45), chr(61931), font=self.icon_font, fill=255)  # Wi-Fi icon

        # Display the actual values
        self.draw.text((19, 5), str(CPU, 'utf-8'), font=self.font, fill=255)
        self.draw.text((87, 5), str(Temperature, 'utf-8'), font=self.font, fill=255)
        self.draw.text((19, 25), str(MemUsage, 'utf-8'), font=self.font, fill=255)
        self.draw.text((87, 25), str(Disk, 'utf-8'), font=self.font, fill=255)
        self.draw.text((19, 45), str(IP, 'utf-8'), font=self.font, fill=255)

        # Display image on OLED
        self.oled1.display(self.image)

    def on_unload(self, ui):
        self.oled1.Clear()
		#insert wait to clear screen
        self.draw.rectangle((0, 0, self.width, self.height), outline=0, fill=0)
        self.oled1.display(self.image)
        logging.info("OLED-Stats plugin unloaded.")