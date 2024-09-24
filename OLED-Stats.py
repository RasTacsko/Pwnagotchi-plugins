import os
import time
import logging
from PIL import Image, ImageDraw, ImageFont
from pwnagotchi.ui.hw.libs.i2coled.epd import EPD
import pwnagotchi.plugins as plugins
import pwnagotchi
from datetime import datetime

class OLEDStats(plugins.Plugin):
    __author__ = 'https://github.com/RasTacsko'
    __version__ = '0.3.0'
    __license__ = 'GPL3'

    def __init__(self):
        self.I2C1 = 0x3C
        self.I2C2 = 0x3D
        self.WIDTH = 128
        self.HEIGHT = 64
        
        self.active = True
        self.ip_index = 0  # Track the current IP to display
        self.last_update = time.time()  # Last time system stats were updated
        self.last_ip_change = time.time()  # Last time the IP address was changed
        self.stats_interval = 3  # Update system stats every 30 seconds
        self.ip_change_interval = 5  # Change IP address display every 10 seconds

        # Cache for system stats
        self.CPU = "N/A"
        self.MemUsage = "N/A"
        self.Disk = "N/A"
        self.Temperature = "N/A"
        self.ip_addresses = ["N/A"]  # Cache for IP addresses

        # Get the directory of this script
        self.plugin_dir = os.path.dirname(os.path.realpath(__file__))
        # Load fonts using absolute paths
        font_path = os.path.join(self.plugin_dir, './OLEDstats/PixelOperator.ttf')
        self.font = ImageFont.truetype(font_path, 14)
        data_font_path = os.path.join(self.plugin_dir, './OLEDstats/chintzy.ttf')
        self.data_font = ImageFont.truetype(data_font_path, 24)
        icon_font_path = os.path.join(self.plugin_dir, './OLEDstats/lineawesome-webfont.ttf')
        self.icon_font = ImageFont.truetype(icon_font_path, 16)

        # Initialize OLED display1
        self.oled1 = EPD(address=self.I2C1, width=self.WIDTH, height=self.HEIGHT)
        self.oled1.Init()
        self.oled1.Clear()
        self.width = self.oled1.width
        self.height = self.oled1.height
        self.image1 = Image.new('1', (self.width, self.height))
        self.draw1 = ImageDraw.Draw(self.image1)

        # Initialize OLED display2
        self.oled2 = EPD(address=self.I2C2, width=self.WIDTH, height=self.HEIGHT)
        self.oled2.Init()
        self.oled2.Clear()
        self.width = self.oled2.width
        self.height = self.oled2.height
        self.image2 = Image.new('1', (self.width, self.height))
        self.draw2 = ImageDraw.Draw(self.image2)

        # Fetch initial stats
        self.update_stats()

    def update_stats(self):
        """Update system stats and IP addresses if the interval has passed"""
        current_time = time.time()
        if current_time - self.last_update >= self.stats_interval:
            try:
                # Use pwnagotchi's built-in methods for CPU, memory, and temperature
                self.CPU = f"{int(pwnagotchi.cpu_load() * 100)}%"  # CPU load in percentage
                self.MemUsage = f"{int(pwnagotchi.mem_usage() * 100)}%"  # Memory usage in percentage
                self.Temperature = f"{pwnagotchi.temperature()}C"  # Temperature in Celsius

                # Update disk usage using os.statvfs
                statvfs = os.statvfs('/')
                total_disk = statvfs.f_frsize * statvfs.f_blocks  # Total disk space in bytes
                free_disk = statvfs.f_frsize * statvfs.f_bfree  # Free disk space in bytes
                used_disk = total_disk - free_disk
                disk_usage_percentage = (used_disk / total_disk) * 100
                total_gb = total_disk / (1024 ** 3)
                free_gb = free_disk / (1024 ** 3)
                used_gb = used_disk / (1024 ** 3)

                self.Disk = f"{int(disk_usage_percentage)}%"
                self.DiskGB = f"{int(free_gb)}/{int(total_gb)}GB free"

                # Update IP addresses
                ip_output = os.popen("hostname -I").read().strip()  # Fetch IP addresses
                self.ip_addresses = ip_output.split(' ') if ip_output else ["Unavailable"]

            except Exception as e:
                logging.error(f"Failed to update system stats: {e}")

            # Update timestamp for the last update
            self.last_update = current_time

    def on_loaded(self):
        logging.info("OLED-Stats plugin loaded")

    def on_ui_update(self, ui):
        if not self.active:
            return  # Exit if the plugin has been unloaded

        # Update system stats and IP addresses at regular intervals
        self.update_stats()

        # Clear image1 (first OLED screen)
        self.draw1.rectangle((0, 0, self.width, self.height), outline=0, fill=0)
        # Draw icons and system stats
        self.draw1.rectangle((0, 0, 15, 15), outline=255, fill=0)
        self.draw1.text((0, 1), chr(62171), font=self.icon_font, fill=255)  # CPU icon
        self.draw1.text((19, 1), self.CPU, font=self.font, fill=255)

        self.draw1.rectangle((0, 16, 15, 33), outline=255, fill=0)
        self.draw1.text((0, 17), chr(62609), font=self.icon_font, fill=255)  # Temperature icon
        self.draw1.text((19, 17), self.Temperature, font=self.font, fill=255)

        self.draw1.rectangle((0, 34, 15, 47), outline=255, fill=0)
        self.draw1.text((0, 33), chr(62776), font=self.icon_font, fill=255)  # Memory icon
        self.draw1.text((19, 33), self.MemUsage, font=self.font, fill=255)

        self.draw1.rectangle((0, 48, 15, 63), outline=255, fill=0)
        self.draw1.text((0, 49), chr(63426), font=self.icon_font, fill=255)  # Disk icon
        self.draw1.text((19, 49), self.Disk, font=self.font, fill=255)
        self.draw1.text((48, 49), self.DiskGB, font=self.font, fill=255)


        # Display image on OLED1
        self.oled1.display(self.image1)

        # Clear image2 (second OLED screen)
        self.draw2.rectangle((0, 0, self.width, self.height), outline=0, fill=0)
        # Get current date and time
        now = datetime.now()
        date_str = now.strftime("%y-%m-%d")
        time_str = now.strftime("%H %M %S")
        # Write the date and time to the second screen
        self.draw2.text((0, 0), date_str, font=self.data_font, fill=255)
        self.draw2.text((0, 26), time_str, font=self.data_font, fill=255)

        self.draw2.rectangle((0, 48, 15, 63), outline=255, fill=0)
        self.draw2.text((0, 49), chr(61931), font=self.icon_font, fill=255)  # Wi-Fi icon

        # Change IP address display based on the IP change interval
        current_time = time.time()
        if current_time - self.last_ip_change >= self.ip_change_interval:
            self.ip_index = (self.ip_index + 1) % len(self.ip_addresses)
            self.last_ip_change = current_time

        # Display the current IP address
        current_ip = self.ip_addresses[self.ip_index]
        self.draw2.text((19, 49), current_ip, font=self.font, fill=255)

        # Display the image on OLED2
        self.oled2.display(self.image2)

    def on_unload(self, ui):
        # Set the active flag to False to stop updates
        self.active = False
        # Wait to ensure the ui_update is stopped
        time.sleep(1.0)
        # Clear the OLED displays
        self.draw1.rectangle((0, 0, self.width, self.height), outline=0, fill=0)
        self.oled1.display(self.image1)
        self.draw2.rectangle((0, 0, self.width, self.height), outline=0, fill=0)
        self.oled2.display(self.image2)
        logging.info("OLED-Stats plugin unloaded and screens turned off")
