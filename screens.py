		#first screen CPU
        self.draw1.rectangle((16, 0, 128, 63), outline=255, fill=255)
        self.draw1.rectangle((0, 0, 15, 15), outline=255, fill=255)
        self.draw1.text((0, 1), chr(62171), font=self.icon_font, fill=0)  # CPU icon
        self.draw1.rectangle((0, 16, 15, 33), outline=0, fill=0)
        self.draw1.text((0, 17), chr(62609), font=self.icon_font, fill=255)  # Temperature icon
        self.draw1.rectangle((0, 34, 15, 47), outline=0, fill=0)
        self.draw1.text((0, 33), chr(62776), font=self.icon_font, fill=255)  # Memory icon
        self.draw1.rectangle((0, 48, 15, 63), outline=0, fill=0)
        self.draw1.text((0, 49), chr(63426), font=self.icon_font, fill=255)  # Disk icon
        self.draw1.text((19, 1), self.CPU, font=self.font, fill=0)
        self.oled1.display(self.image1)
        time.sleep(5.0)
		#second screen Temperature
        self.draw1.rectangle((16, 0, 128, 63), outline=255, fill=255)
        self.draw1.rectangle((0, 0, 15, 15), outline=0, fill=0)
        self.draw1.text((0, 1), chr(62171), font=self.icon_font, fill=255)  # CPU icon
        self.draw1.rectangle((0, 16, 15, 33), outline=255, fill=255)
        self.draw1.text((0, 17), chr(62609), font=self.icon_font, fill=0)  # Temperature icon
        self.draw1.rectangle((0, 34, 15, 47), outline=0, fill=0)
        self.draw1.text((0, 33), chr(62776), font=self.icon_font, fill=255)  # Memory icon
        self.draw1.rectangle((0, 48, 15, 63), outline=0, fill=0)
        self.draw1.text((0, 49), chr(63426), font=self.icon_font, fill=255)  # Disk icon
        self.draw1.text((19, 17), self.Temperature, font=self.font, fill=0)
        self.oled1.display(self.image1)
        time.sleep(5.0)
		#third screen Memory
        self.draw1.rectangle((16, 0, 128, 63), outline=255, fill=255)
        self.draw1.rectangle((0, 0, 15, 15), outline=0, fill=0)
        self.draw1.text((0, 1), chr(62171), font=self.icon_font, fill=0)  # CPU icon
        self.draw1.rectangle((0, 16, 15, 33), outline=0, fill=0)
        self.draw1.text((0, 17), chr(62609), font=self.icon_font, fill=255)  # Temperature icon
        self.draw1.rectangle((0, 34, 15, 47), outline=255, fill=255)
        self.draw1.text((0, 33), chr(62776), font=self.icon_font, fill=0)  # Memory icon
        self.draw1.rectangle((0, 48, 15, 63), outline=0, fill=0)
        self.draw1.text((0, 49), chr(63426), font=self.icon_font, fill=255)  # Disk icon
        self.draw1.text((19, 33), self.MemUsage, font=self.font, fill=0)
        self.oled1.display(self.image1)
        time.sleep(5.0)
		#fourth screen Disk
        self.draw1.rectangle((16, 0, 128, 63), outline=255, fill=255)
        self.draw1.rectangle((0, 0, 15, 15), outline=0, fill=0)
        self.draw1.text((0, 1), chr(62171), font=self.icon_font, fill=0)  # CPU icon
        self.draw1.rectangle((0, 16, 15, 33), outline=0, fill=0)
        self.draw1.text((0, 17), chr(62609), font=self.icon_font, fill=255)  # Temperature icon
        self.draw1.rectangle((0, 34, 15, 47), outline=0, fill=0)
        self.draw1.text((0, 33), chr(62776), font=self.icon_font, fill=255)  # Memory icon
        self.draw1.rectangle((0, 48, 15, 63), outline=255, fill=255)
        self.draw1.text((0, 49), chr(63426), font=self.icon_font, fill=0)  # Disk icon
        self.draw1.text((19, 49), self.Disk, font=self.font, fill=0)
        self.draw1.text((48, 49), self.DiskGB, font=self.font, fill=0)
        self.oled1.display(self.image1)
        time.sleep(5.0)