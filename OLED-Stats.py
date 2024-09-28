import os
import time
import logging
import threading
from datetime import datetime
from PIL import Image, ImageDraw, ImageFont
import pwnagotchi
import pwnagotchi.plugins as plugins
from pwnagotchi.ui.hw.libs.i2coled.epd import EPD

class OLEDStats(plugins.Plugin):
    __author__ = 'https://github.com/RasTacsko'
    __version__ = '0.3.1'
    __license__ = 'GPL3'
    __description__ = 'Hardware monitor for the waveshare OLED/LCD screen'
    __defaults__ = {
        'color': False,
    }
# to change to light bg main.plugins.OLED-Stats2.color = light/dark/auto

    def __init__(self):
        self.I2C1 = 0x3C
        self.I2C2 = 0x3D
        self.WIDTH = 128
        self.HEIGHT = 64
        
        self.active = True
        self.screen_index = 0  # Track the current screen to display
        self.last_update = time.time()  # Last time system stats were updated
        self.screen_update_interval = 5  # Change screen display and refresh stats every 5 seconds

        # Cache for system stats
        self.CPU = "N/A"
        self.MemUsage = "N/A"
        self.Disk = "N/A"
        self.Temperature = "N/A"
        self.ip_addresses = ["N/A"]  # Cache for IP addresses
        self.ip_index = 0  # Track the current IP to display

        # Get the directory of this script
        self.plugin_dir = os.path.dirname(os.path.realpath(__file__))
        
        # Load fonts using absolute paths
        font_path = os.path.join(self.plugin_dir, './OLEDstats/CyborgPunk.ttf')
        self.font = ImageFont.truetype(font_path, 10)
        data_font_path = os.path.join(self.plugin_dir, './OLEDstats/CyborgPunk.ttf')
        self.data_font = ImageFont.truetype(data_font_path, 26)
        icon_font_path = os.path.join(self.plugin_dir, './OLEDstats/lineawesome-webfont.ttf')
        self.icon_font = ImageFont.truetype(icon_font_path, 16)

        # Initialize OLED display 1
        self.oled1 = EPD(address=self.I2C1, width=self.WIDTH, height=self.HEIGHT)
        self.oled1.Init()
        self.oled1.Clear()
        self.image1 = Image.new('1', (self.WIDTH, self.HEIGHT))
        self.draw1 = ImageDraw.Draw(self.image1)

        # Initialize OLED display 2
        self.oled2 = EPD(address=self.I2C2, width=self.WIDTH, height=self.HEIGHT)
        self.oled2.Init()
        self.oled2.Clear()
        self.image2 = Image.new('1', (self.WIDTH, self.HEIGHT))
        self.draw2 = ImageDraw.Draw(self.image2)

        # Fetch initial stats
        self.update_stats()
        logging.info("init done")

    def update_stats(self):
        # Update system stats and IP addresses
        try:
            # Update CPU, RAM and Temp data
            self.CPU = f"{int(pwnagotchi.cpu_load() * 100)}%"
            self.MemUsage = f"{int(pwnagotchi.mem_usage() * 100)}%"
            self.Temperature = f"{pwnagotchi.temperature()}C"

            # Update disk usage using os.statvfs
            statvfs = os.statvfs('/')
            total_disk = statvfs.f_frsize * statvfs.f_blocks
            free_disk = statvfs.f_frsize * statvfs.f_bfree
            used_disk = total_disk - free_disk
            disk_usage_percentage = (used_disk / total_disk) * 100
            total_gb = total_disk / (1024 ** 3)
            free_gb = free_disk / (1024 ** 3)
            self.Disk = f"{int(disk_usage_percentage)}%"
            self.DiskGB = f"{int(free_gb)}/{int(total_gb)}GB free"

            # Update IP addresses
            ip_output = os.popen("hostname -I").read().strip()
            self.ip_addresses = ip_output.split(' ') if ip_output else ["Unavailable"]

            # Get current date and time 
            now = datetime.now()
            self.date_str = now.strftime("%y-%m-%d")
            self.time_str = now.strftime("%H:%M")
            logging.info("stats update done")

        except Exception as e:
            logging.error(f"Failed to update system stats: {e}")

    def on_loaded(self):
        # Load configuration for color inversion
        logging.info("OLED-Stats plugin loaded")

    def on_ui_update(self, ui):
        # Exit if the plugin has been unloaded
        if not self.active:
            return
        self.color = self.options.get('color', False)
        # If set to auto, change color inversion based on time of day
        if self.color == "auto":
            current_hour = datetime.now().hour
            if 6 <= current_hour < 17:
                self.fill_color = 0  # Invert during daytime (6 AM to 6 PM)
                self.bg_color = 255
                logging.info("Screen inverted for daytime (6 AM - 6 PM)")
            else:
                self.fill_color = 255  # Normal at night (6 PM to 6 AM)
                self.bg_color = 0
                logging.info("Screen normal for nighttime (6 PM - 6 AM)")
        elif self.color == "light":
            self.fill_color = 0
            self.bg_color = 255
            logging.info("Screen inverted")
        else:
            self.fill_color = 255
            self.bg_color = 0
            logging.info("Screen normal")

        # Get the current time
        current_time = time.time()    
        logging.info("ui update started")

        # Update system stats and screens if the update interval has passed
        if current_time - self.last_update >= self.screen_update_interval:
            self.update_stats()
            self.screen_index = (self.screen_index + 1) % 4  # Cycle through 4 screens
            self.ip_index = (self.ip_index + 1) % len(self.ip_addresses)
            self.last_update = current_time  # Update the last screen change timestamp
            # Clear both OLED screens
            self.draw1.rectangle((0, 0, self.WIDTH, self.HEIGHT), outline=0, fill=self.bg_color)
            self.draw2.rectangle((0, 0, self.WIDTH, self.HEIGHT), outline=0, fill=self.bg_color)
            logging.info("screens cleared")

            # Draw static icons for both screens with dynamic fills based on the current screen
            cpu_fill = self.fill_color if self.screen_index == 0 else self.bg_color
            temp_fill = self.fill_color if self.screen_index == 1 else self.bg_color
            mem_fill = self.fill_color if self.screen_index == 2 else self.bg_color
            disk_fill = self.fill_color if self.screen_index == 3 else self.bg_color
            # Background fill parameters for active/inactive screens
            cpu_bg_fill = self.bg_color if self.screen_index == 0 else self.fill_color
            temp_bg_fill = self.bg_color if self.screen_index == 1 else self.fill_color
            mem_bg_fill = self.bg_color if self.screen_index == 2 else self.fill_color
            disk_bg_fill = self.bg_color if self.screen_index == 3 else self.fill_color
            logging.info("icons color")

            # Screen 1 layout with icons and system stats
            self.draw1.rectangle((0, 0, 15, 15), outline=cpu_bg_fill, fill=cpu_bg_fill)
            self.draw1.text((0, 1), chr(62171), font=self.icon_font, fill=cpu_fill)  # CPU icon
            self.draw1.rectangle((0, 16, 15, 33), outline=temp_bg_fill, fill=temp_bg_fill)
            self.draw1.text((0, 17), chr(62609), font=self.icon_font, fill=temp_fill)  # Temperature icon
            self.draw1.rectangle((0, 34, 15, 47), outline=mem_bg_fill, fill=mem_bg_fill)
            self.draw1.text((0, 33), chr(62776), font=self.icon_font, fill=mem_fill)  # Memory icon
            self.draw1.rectangle((0, 48, 15, 63), outline=disk_bg_fill, fill=disk_bg_fill)
            self.draw1.text((0, 49), chr(63426), font=self.icon_font, fill=disk_fill)  # Disk icon
            logging.info("icons drawn")

            # Display specific stat on screen 1
            if self.screen_index == 0:
                self.draw1.text((19, 0), f"CPU", font=self.font, fill=self.fill_color)
                self.draw1.text((26, 10), self.CPU, font=self.data_font, fill=self.fill_color)
            elif self.screen_index == 1:
                self.draw1.text((19, 0), f"TEMP", font=self.font, fill=self.fill_color)
                self.draw1.text((26, 10), self.Temperature, font=self.data_font, fill=self.fill_color)
            elif self.screen_index == 2:
                self.draw1.text((19, 0), f"RAM", font=self.font, fill=self.fill_color)
                self.draw1.text((26, 10), self.MemUsage, font=self.data_font, fill=self.fill_color)
            elif self.screen_index == 3:
                self.draw1.text((19, 0), f"HDD", font=self.font, fill=self.fill_color)
                self.draw1.text((26, 10), f"{self.Disk}", font=self.data_font, fill=self.fill_color)
                self.draw1.text((19, 49), f"{self.DiskGB}", font=self.font, fill=self.fill_color)
            logging.info("display1 screen drawn")

            # Screen 2 layout (show IP addresses and any other info)
            # Write the date and time to the second screen
            self.draw2.text((19, 0), self.date_str, font=self.font, fill=self.fill_color)
            self.draw2.text((19, 10), self.time_str, font=self.data_font, fill=self.fill_color)
            logging.info("time drawn")

            # Write the IP address with a wifi icon
            self.draw2.rectangle((0, 48, 15, 63), outline=self.bg_color, fill=self.bg_color)
            self.draw2.text((0, 49), chr(61931), font=self.icon_font, fill=self.fill_color)  # Wi-Fi icon
            self.draw2.text((19, 49), self.ip_addresses[self.ip_index], font=self.font, fill=self.fill_color)
            logging.info("ip drawn")

            # Display the images on both screens
            self.oled1.display(self.image1)
            self.oled2.display(self.image2)
            logging.info("send fb to screen")
        logging.info(f"Active threads after update: {threading.active_count()}")

    def on_unload(self, ui):
        self.active = False
        self.draw1.rectangle((0, 0, self.WIDTH, self.HEIGHT), outline=0, fill=0)
        self.draw2.rectangle((0, 0, self.WIDTH, self.HEIGHT), outline=0, fill=0)
        self.oled1.display(self.image1)
        self.oled2.display(self.image2)
        logging.info("OLED-Stats plugin unloaded and screens turned off")