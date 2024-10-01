import logging
from gpiozero import Button, RotaryEncoder
import subprocess
import time
import pwnagotchi.plugins as plugins

class GPIOControl(plugins.Plugin):
    __author__ = 'https://github.com/RasTacsko'
    __version__ = '0.1.8'
    __license__ = 'GPL3'
    __description__ = 'GPIO Button and Rotary Encoder support plugin with press, hold, and rotate logic.'

    def __init__(self):
        self.buttons = {}
        self.button_hold_times = {}  # Track button press times
        self.encoder = None
        self.encoder_button = None

    def runcommand(self, command):
        logging.info(f"Running command: {command}")
        process = subprocess.Popen(command, shell=True, stdin=None, stdout=open("/dev/null", "w"), stderr=None,
                                   executable="/bin/bash")
        process.wait()

    def on_loaded(self):
        logging.info("GPIO Button and Encoder plugin loaded.")

        # Initialize GPIO buttons
        gpios = self.options.get('gpios', {})
        for gpio, actions in gpios.items():
            gpio = int(gpio)
            button = Button(gpio, pull_up=True, bounce_time=0.05, hold_time=1.0)
            short_press_command = actions.get('short_press')
            long_press_command = actions.get('long_press')
            button.when_pressed = lambda btn=button, gpio=gpio: self.on_button_pressed(gpio)
            button.when_released = lambda btn=button, gpio=gpio, short_press_command=short_press_command, long_press_command=long_press_command: self.on_button_released(gpio, short_press_command, long_press_command)
            self.buttons[gpio] = button
            logging.info(f"Configured GPIO #{gpio} for short press: {short_press_command} and long press: {long_press_command}")

        # Initialize Encoder and encoder button
        encoder_pins = self.options.get('encoder', {})
        encoder_a = encoder_pins.get('a')
        encoder_b = encoder_pins.get('b')
        encoder_button_pin = encoder_pins.get('button')
        encoder_up_command = encoder_pins.get('up_command')
        encoder_down_command = encoder_pins.get('down_command')

        if encoder_a and encoder_b:
            self.encoder = RotaryEncoder(encoder_a, encoder_b, max_steps=1000, bounce_time=0.01)
            self.encoder.when_rotated = lambda: self.on_encoder_rotated(encoder_up_command, encoder_down_command)
            logging.info(f"Encoder configured with pins A: {encoder_a}, B: {encoder_b}")
        if encoder_button_pin:
            self.encoder_button = Button(encoder_button_pin, pull_up=True, bounce_time=0.05, hold_time=1.0)
            self.encoder_button.when_pressed = lambda: self.on_button_pressed(encoder_button_pin)
            self.encoder_button.when_released = lambda: self.on_button_released(encoder_button_pin, encoder_pins.get('button_short_press'), encoder_pins.get('button_long_press'))
            logging.info(f"Encoder button configured on GPIO {encoder_button_pin}.")

    def on_button_pressed(self, gpio):
        """Record the time the button was pressed."""
        self.button_hold_times[gpio] = time.time()
        logging.debug(f"Button {gpio} pressed.")

    def on_button_released(self, gpio, short_press_command, long_press_command):
        """Handle button release and determine if it's a short or long press."""
        hold_time = time.time() - self.button_hold_times[gpio]
        logging.info(f"Button {gpio} released after {hold_time:.2f} seconds.")
        if hold_time >= 1.0:
            logging.info(f"Long press detected on GPIO {gpio}. Running command: {long_press_command}")
            if long_press_command:
                self.runcommand(long_press_command)
        else:
            logging.info(f"Short press detected on GPIO {gpio}. Running command: {short_press_command}")
            if short_press_command:
                self.runcommand(short_press_command)

    def on_encoder_rotated(self, up_command, down_command):
        """Handle encoder rotation."""
        steps = self.encoder.steps
        if steps > 0:
            logging.info(f"Encoder rotated up. Running command: {up_command}")
            if up_command:
                self.runcommand(up_command)
        elif steps < 0:
            logging.info(f"Encoder rotated down. Running command: {down_command}")
            if down_command:
                self.runcommand(down_command)

    def on_unload(self, ui):
        logging.info("GPIO Button and Encoder control plugin unloaded.")