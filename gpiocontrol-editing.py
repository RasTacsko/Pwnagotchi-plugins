import logging
from gpiozero import Button, RotaryEncoder
import subprocess
import pwnagotchi.plugins as plugins
import toml

class GPIOControl(plugins.Plugin):
    __author__ = 'https://github.com/RasTacsko'
    __version__ = '0.2.0' #updated with the help of chat GPT to simplify the code and separate short/long press commands
    __license__ = 'GPL3'
    __description__ = 'GPIO Button and Rotary Encoder control plugin with press, hold, and rotate functionality'

    def __init__(self):
        self.buttons = {}
        self.encoder = None
        self.config = None
        self.encoder_up_command = None
        self.encoder_down_command = None
        self.encoder_button = None
        self.button_hold_flags = {}  # Track which buttons have triggered a hold

    def load_config(self, config_path):
        """Load the configuration from a TOML file."""
        try:
            with open(config_path, 'r') as file:
                self.config = toml.load(file)
            logging.info("Configuration loaded successfully.")
        except Exception as e:
            logging.error(f"Failed to load config: {e}")
            self.config = {}

    def run_command(self, command):
        """Run a shell command."""
        if command:
            logging.info(f"Running command: {command}")
            subprocess.Popen(command, shell=True, stdin=None, stdout=None, stderr=None, executable="/bin/bash")

    def on_button_pressed(self, gpio):
        """Handle button press."""
        if not self.button_hold_flags[gpio]:  # Only handle press if not holding
            command = self.config.get(f'main.plugins.gpiocontrol.gpios.{gpio}.short_press')
            if command:
                logging.info(f"Short press detected on GPIO {gpio}.")
                self.run_command(command)

    def on_button_held(self, gpio):
        """Handle button hold."""
        self.button_hold_flags[gpio] = True  # Mark as held
        command = self.config.get(f'main.plugins.gpiocontrol.gpios.{gpio}.long_press')
        if command:
            logging.info(f"Long press detected on GPIO {gpio}.")
            self.run_command(command)

    def on_button_released(self, gpio):
        """Handle button release. Reset hold flag."""
        self.button_hold_flags[gpio] = False

    def on_encoder_rotate(self):
        """Handle encoder rotation."""
        steps = self.encoder.steps
        if steps > 0:
            logging.info(f"Encoder rotated up. Steps: {steps}")
            self.run_command(self.encoder_up_command)
        elif steps < 0:
            logging.info(f"Encoder rotated down. Steps: {steps}")
            self.run_command(self.encoder_down_command)

    def on_loaded(self):
        """Initialize the GPIO controls."""
        logging.info("GPIO Button and Encoder control plugin loaded.")
        self.load_config('/path/to/config.toml')  # Path to config.toml

        # Initialize GPIO buttons
        gpios = self.config.get('main.plugins.gpiocontrol.gpios', {})
        for gpio_str, actions in gpios.items():
            gpio = int(gpio_str)
            button = Button(gpio, pull_up=True, bounce_time=0.05, hold_time=1.0)
            self.button_hold_flags[gpio] = False  # Initialize hold flag for each button

            button.when_pressed = lambda btn=button, gpio=gpio: self.on_button_pressed(gpio)
            button.when_held = lambda btn=button, gpio=gpio: self.on_button_held(gpio)
            button.when_released = lambda btn=button, gpio=gpio: self.on_button_released(gpio)

            self.buttons[gpio] = button
            logging.info(f"Configured GPIO {gpio} for short/long press actions.")

        # Initialize Encoder
        encoder_pins = self.config.get('main.plugins.gpiocontrol.encoder', {})
        encoder_a = encoder_pins.get('a')
        encoder_b = encoder_pins.get('b')
        button_pin = encoder_pins.get('button')

        self.encoder_up_command = encoder_pins.get('up_command')
        self.encoder_down_command = encoder_pins.get('down_command')

        if encoder_a and encoder_b:
            self.encoder = RotaryEncoder(encoder_a, encoder_b, max_steps=1000, bounce_time=0.01)
            self.encoder.when_rotated = self.on_encoder_rotate
            logging.info(f"Encoder configured with pins A: {encoder_a}, B: {encoder_b}")

        # Initialize Encoder button
        if button_pin:
            self.encoder_button = Button(button_pin, pull_up=True, bounce_time=0.05, hold_time=1.0)
            self.encoder_button.when_pressed = lambda: self.on_button_pressed(button_pin)
            self.encoder_button.when_held = lambda: self.on_button_held(button_pin)
            self.encoder_button.when_released = lambda: self.on_button_released(button_pin)

            logging.info(f"Encoder button configured on GPIO {button_pin}.")

    def on_unload(self, ui):
        """Stop the plugin and cleanup."""
        logging.info("GPIO Button and Encoder control plugin unloaded.")
