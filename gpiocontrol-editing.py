import logging
from gpiozero import Button, RotaryEncoder
import subprocess
import pwnagotchi.plugins as plugins

class GPIOControl(plugins.Plugin):
    __author__ = 'https://github.com/RasTacsko'
    __version__ = '0.1.2'
    __license__ = 'GPL3'
    __description__ = 'GPIO Button and Rotary Encoder support plugin with long/short press functionality'

    def __init__(self):
        self.running = False
        self.buttons = {}
        self.encoder = None
        self.commands = None
        self.options = dict()
        self.encoder_up_command = None
        self.encoder_down_command = None
        self.previous_step = 0  # To track encoder steps

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
            button = Button(gpio, pull_up=True, bounce_time=0.15, hold_time=1.0)  # hold_time is set to 1 second

            short_press_command = actions.get('short_press')
            long_press_command = actions.get('long_press')

            if short_press_command:
                # Use a default argument to bind the specific command to the event
                button.when_pressed = lambda btn=button, cmd=short_press_command: self.runcommand(cmd)
            if long_press_command:
                # Use a default argument to bind the specific command to the event
                button.when_held = lambda btn=button, cmd=long_press_command: self.runcommand(cmd)

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
                logging.info(f"Encoder configured with pins A: {encoder_a}, B: {encoder_b}")

            if button_pin:
                short_press_command = encoder_pins.get('short_press')
                long_press_command = encoder_pins.get('long_press')

                self.encoder_button = Button(button_pin, pull_up=True, bounce_time=0.15, hold_time=1.0)
                if short_press_command:
                    self.encoder_button.when_pressed = lambda btn=button, cmd=short_press_command: self.runcommand(cmd)
                if long_press_command:
                    self.encoder_button.when_held = lambda btn=button, cmd=long_press_command: self.runcommand(cmd)

                logging.info(f"Encoder button configured on pin: {button_pin} for short press: {short_press_command} and long press: {long_press_command}")

    def on_encoder_rotate(self):
        direction = self.encoder.steps  # The direction of rotation
        if direction > 0:
            logging.info("Encoder rotated up (clockwise). Running command: %s", self.encoder_up_command)
            self.runcommand(self.encoder_up_command)
        elif direction < 0:
            logging.info("Encoder rotated down (counterclockwise). Running command: %s", self.encoder_down_command)
            self.runcommand(self.encoder_down_command)
        else:
            logging.info("Encoder rotation detected, but no direction determined.")

    def on_encoder_button_press(self):
        if self.encoder_button:
            logging.info("Encoder button pressed!")

    def on_unload(self):
        logging.info("GPIO Button and Encoder control plugin unloaded.")
