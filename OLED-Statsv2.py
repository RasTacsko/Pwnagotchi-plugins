import os
import time
import logging
from PIL import Image, ImageDraw, ImageFont
from pwnagotchi.ui.hw.libs.i2coled.epd import EPD
import subprocess
import pwnagotchi.plugins as plugins
from datetime import datetime

class OLEDStats(plugins.Plugin):
    __author__ = 'https://github.com/RasTacsko'
    __version__ = '0.2.0'
    __license__ = 'GPL3'

    def __init__(self):
        self.I2C1 = 0x3C
        self.I2C2 = 0x3D
        self.WIDTH = 128
        self.HEIGHT = 64
        self.FONTSIZE = 16
        
        self.active = True
        self.ip_index = 0  # Track the current IP to display
        self.ip_last_update = time.time()  # Last time IP was updated

        # Get all IP addresses at startup
        self.ip_addresses = self.get_ip_addresses()

        # Get the directory of this script
        self.plugin_dir = os.path.dirname(os.path.realpath(__file__))
        # Load fonts using absolute paths
        font_path = os.path.join(self.plugin_dir, 'PixelOperator.ttf')
        icon_font_path = os.path.join(self.plugin_dir, 'lineawesome-webfont.ttf')
        self.font = ImageFont.truetype(font_path, 16)
        self.icon_font = ImageFont.truetype(icon_font_path, 18)

        # Initialize OLED display
        self.oled1 = EPD(address=self.I2C1, width=self.WIDTH, height=self.HEIGHT)
        self.oled1.Init()
        self.oled1.Clear()
        # Create blank image for drawing
        self.width = self.oled1.width
        self.height = self.oled1.height
        self.image1 = Image.new('1', (self.width, self.height))
        self.draw1 = ImageDraw.Draw(self.image1)

        # Initialize OLED display2
        self.oled2 = EPD(address=self.I2C2, width=self.WIDTH, height=self.HEIGHT)
        self.oled2.Init()
        self.oled2.Clear()
        # Create blank image for drawing
        self.width = self.oled2.width
        self.height = self.oled2.height
        # Create blank image for the second screen
        self.image2 = Image.new('1', (self.width, self.height))
        self.draw2 = ImageDraw.Draw(self.image2)


    def get_ip_addresses(self):
        # Fetch all IP addresses
        ip_output = subprocess.check_output("hostname -I", shell=True)
        ip_list = ip_output.decode('utf-8').strip().split(' ')
        return ip_list if ip_list else ["Unavailable"]

    def on_loaded(self):
        logging.info("OLED-Stats plugin loaded")

    def on_ui_update(self, ui):
        if not self.active:
            return  # Exit if the plugin has been unloaded
        # Clear image1
        self.draw1.rectangle((0, 0, self.width, self.height), outline=0, fill=0)
        # System monitoring commands
        CPU = subprocess.check_output("top -bn1 | grep load | awk '{printf \"%.2fLA\", $(NF-2)}'", shell=True)
        MemUsage = subprocess.check_output("free -m | awk 'NR==2{printf \"%.2f%%\", $3*100/$2 }'", shell=True)
        Disk = subprocess.check_output("df -h | awk '$NF==\"/\"{printf \"%d/%dGB\", $3,$2}'", shell=True)
        Temperature = subprocess.check_output("vcgencmd measure_temp | cut -d '=' -f 2 | head --bytes -1", shell=True)

        # Draw icons and stats
        self.draw1.text((0, 5), chr(62171), font=self.icon_font, fill=255)  # CPU icon
        self.draw1.text((65, 5), chr(62609), font=self.icon_font, fill=255)  # Temperature icon
        self.draw1.text((0, 25), chr(62776), font=self.icon_font, fill=255)  # Memory icon
        self.draw1.text((65, 25), chr(63426), font=self.icon_font, fill=255)  # Disk icon
        self.draw1.text((0, 45), chr(61931), font=self.icon_font, fill=255)  # Wi-Fi icon
        # Display the actual values
        self.draw1.text((19, 5), str(CPU, 'utf-8'), font=self.font, fill=255)
        self.draw1.text((87, 5), str(Temperature, 'utf-8'), font=self.font, fill=255)
        self.draw1.text((19, 25), str(MemUsage, 'utf-8'), font=self.font, fill=255)
        self.draw1.text((87, 25), str(Disk, 'utf-8'), font=self.font, fill=255)
#        self.draw1.text((19, 45), str(IP, 'utf-8'), font=self.font, fill=255)
        # Cycle through IP addresses every 3 seconds
        current_time = time.time()
        if current_time - self.ip_last_update >= 3:
            self.ip_index = (self.ip_index + 1) % len(self.ip_addresses)  # Increment index and cycle
            self.ip_last_update = current_time
        
        current_ip = self.ip_addresses[self.ip_index]
        self.draw1.text((19, 45), current_ip, font=self.font, fill=255)


        # Display image on OLED1
        self.oled1.display(self.image1)
        
        # Clear image2
        self.draw2.rectangle((0, 0, self.width, self.height), outline=0, fill=0)
        # Get current date and time
        now = datetime.now()
        date_str = now.strftime("%Y-%m-%d")
        time_str = now.strftime("%H:%M:%S")
        # Write the date and time to the second screen
        self.draw2.text((10, 20), date_str, font=self.font, fill=255)
        self.draw2.text((10, 40), time_str, font=self.font, fill=255)
        # Display the image on the second OLED screen
        self.oled2.display(self.image2)

    def on_unload(self, ui):
        # Set the active flag to False to stop updates
        self.active = False
        # Wait to ensure the ui_update is stopped
        time.sleep(1.0)
        # Clear the OLED displays
        self.draw1.rectangle((0, 0, self.width, self.height), outline=0, fill=0)
        self.draw2.rectangle((0, 0, self.width, self.height), outline=0, fill=0)
        self.oled1.display(self.image1)
        self.oled2.display(self.image2)
        # Wait to ensure the displays are cleared
        time.sleep(1.0)
        logging.info("OLED-Stats plugin unloaded and screens turned off")
