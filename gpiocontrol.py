import logging
from gpiozero import Button, RotaryEncoder
import subprocess
import pwnagotchi.plugins as plugins
class GPIOControl(plugins.Plugin):
    __author__ = 'https://github.com/RasTacsko'
    __version__ = '0.1.5'
    __license__ = 'GPL3'
    __description__ = 'GPIO Button and Rotary Encoder support plugin with improved button handling'
    def __init__(self):
        self.running = False
        self.buttons = {}
        self.encoder = None
        self.commands = None
        self.options = dict()
        self.encoder_up_command = None
        self.encoder_down_command = None
        self.previous_step = 0  # To track encoder steps
        self.button_hold_flags = {}  # To track whether a button hold was triggered
    def runcommand(self, command):
        logging.info(f"Running command: {command}")
        process = subprocess.Popen(command, shell=True, stdin=None, stdout=open("/dev/null", "w"), stderr=None,
                                   executable="/bin/bash")
        process.wait()
    def on_loaded(self):
        logging.info("GPIO Button and Encoder plugin loaded.")
        # get list of GPIOs and encoder pin configurations
        gpios = self.options.get('gpios', {})
        encoder_pins = self.options.get('encoder', {})
        for gpio, actions in gpios.items():
            gpio = int(gpio)
            button = Button(gpio, pull_up=True, bounce_time=0.05, hold_time=1.0)  # hold_time is set to 1 second
            short_press_command = actions.get('short_press')
            long_press_command = actions.get('long_press')
            # Track if the button was held (long press)
            self.button_hold_flags[gpio] = False
            if short_press_command or long_press_command:
                # Use a helper function to handle both press and hold
                button.when_pressed = lambda btn=button, gpio=gpio: self.on_button_pressed(gpio, short_press_command, long_press_command)
                button.when_released = lambda btn=button, gpio=gpio: self.on_button_released(gpio)
            self.buttons[gpio] = button
            logging.info("Configured GPIO #%d for short press: %s and long press: %s",
                         gpio, short_press_command, long_press_command)
        if encoder_pins:
            encoder_a = encoder_pins.get('a')
            encoder_b = encoder_pins.get('b')
            button_pin = encoder_pins.get('button')
            self.encoder_up_command = encoder_pins.get('up_command')
            self.encoder_down_command = encoder_pins.get('down_command')
            if encoder_a and encoder_b:
                self.encoder = RotaryEncoder(encoder_a, encoder_b, max_steps=1000, bounce_time=0.01, wrap=True)
                self.encoder.when_rotated = self.on_encoder_rotate
                logging.info(f"Encoder configured with pins A: {encoder_a}, B: {encoder_b} in half-step mode.")
            if button_pin:
                short_press_command = encoder_pins.get('short_press')
                long_press_command = encoder_pins.get('long_press')
                self.encoder_button = Button(button_pin, pull_up=True, bounce_time=0.05, hold_time=1.0)
                if short_press_command or long_press_command:
                    self.encoder_button.when_pressed = lambda: self.on_button_pressed(button_pin, short_press_command, long_press_command)
                    self.encoder_button.when_released = lambda: self.on_button_released(button_pin)
                logging.info(f"Encoder button configured on pin: {button_pin} for short press: {short_press_command} and long press: {long_press_command}")
    def on_button_pressed(self, gpio, short_press_command, long_press_command):
        """Handle button press."""
        self.button_hold_flags[gpio] = False  # Reset hold flag initially
        logging.debug(f"Button {gpio} pressed, waiting for hold or release.")
        if long_press_command:
            # Set up hold handling
            self.buttons[gpio].when_held = lambda: self.on_button_held(gpio, long_press_command)
    def on_button_released(self, gpio):
        """Handle button release (short press)."""
        if not self.button_hold_flags[gpio]:
            short_press_command = self.options.get('gpios', {}).get(str(gpio), {}).get('short_press')
            if short_press_command:
                logging.info(f"Short press detected on GPIO {gpio}. Running command: {short_press_command}")
                self.runcommand(short_press_command)
    def on_button_held(self, gpio, long_press_command):
        """Handle button hold (long press)."""
        self.button_hold_flags[gpio] = True  # Mark as long press, so short press isn't triggered
        logging.info(f"Long press detected on GPIO {gpio}. Running command: {long_press_command}")
        self.runcommand(long_press_command)
    def on_encoder_rotate(self):
        current_step = self.encoder.steps
        logging.debug(f"Current encoder step: {current_step}, Previous step: {self.previous_step}")
        if current_step > self.previous_step:
            logging.info("Encoder rotated up (clockwise). Running command: %s", self.encoder_up_command)
            self.runcommand(self.encoder_up_command)
        elif current_step < self.previous_step:
            logging.info("Encoder rotated down (counterclockwise). Running command: %s", self.encoder_down_command)
            self.runcommand(self.encoder_down_command)
        self.previous_step = current_step
    def on_unload(self, ui):
        logging.info("GPIO Button and Encoder control plugin unloaded.")