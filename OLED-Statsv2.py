import os
import time
import logging
from PIL import Image, ImageDraw, ImageFont
from pwnagotchi.ui.hw.libs.i2coled.epd import EPD
import subprocess
import pwnagotchi.plugins as plugins
from datetime import datetime
import psutil

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

    def on_ui_update(self, ui):
        if not self.active:
            return  # Exit if the plugin has been unloaded
        # Clear image1
        self.draw1.rectangle((0, 0, self.width, self.height), outline=0, fill=0)
        # System monitoring commands
        # IP = subprocess.check_output("hostname -I | cut -d' ' -f1 | head --bytes -1", shell=True)
        # CPU = subprocess.check_output("top -bn1 | grep load | awk '{printf \"%.2fLA\", $(NF-2)}'", shell=True)
        # MemUsage = subprocess.check_output("free -m | awk 'NR==2{printf \"%.2f%%\", $3*100/$2 }'", shell=True)
        # Disk = subprocess.check_output("df -h | awk '$NF==\"/\"{printf \"%d/%dGB\", $3,$2}'", shell=True)
        # Temperature = subprocess.check_output("vcgencmd measure_temp | cut -d '=' -f 2 | head --bytes -1", shell=True)
        def get_ip_address():
            addrs = psutil.net_if_addrs()
            for iface, iface_info in addrs.items():
                for addr in iface_info:
                    if addr.family == psutil.AF_INET and iface != 'lo':
                        return addr.address
            return "Unavailable"
        IP = get_ip_address()
#        IP = psutil.net_if_addrs()['wlan0'][0].address
        CPU = f"{psutil.getloadavg()[0]:.2f}LA"
        MemUsage = f"{psutil.virtual_memory().percent:.2f}%"
        disk_usage = psutil.disk_usage('/')
        Disk = f"{disk_usage.used // (2**30)}/{disk_usage.total // (2**30)}GB"
        temp = psutil.sensors_temperatures()
        if 'coretemp' in temp:
            Temperature = f"{temp['coretemp'][0].current}°C"
        else:
            Temperature = "Unavailable"

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
        self.draw1.text((19, 45), str(IP, 'utf-8'), font=self.font, fill=255)
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

        # Clear the OLED displays
        self.oled1.Clear()
        self.oled2.Clear()

        # Wait to ensure the displays are cleared
        time.sleep(0.5)

        # Turn off the OLED displays (if supported by the driver)
        try:
            self.oled1.Sleep()  # Turn off the first screen
            self.oled2.Sleep()  # Turn off the second screen
        except AttributeError:
            logging.warning("Sleep method not supported for this display driver")
        
        logging.info("OLED-Stats plugin unloaded and screens turned off")