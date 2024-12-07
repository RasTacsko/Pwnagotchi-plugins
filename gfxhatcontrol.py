import logging
import subprocess
import time
from pwnagotchi.ui.hw.libs.pimoroni.gfxhat import touch
import pwnagotchi.plugins as plugins


class GPIOControl(plugins.Plugin):
    __author__ = 'https://github.com/RasTacsko'
    __version__ = '0.1.0'  # Incremented version
    __license__ = 'GPL3'
    __description__ = 'GFX HAT Touch Button plugin with press, hold, and LED control.'

    def __init__(self):
        self.button_hold_times = {}  # Track button press times
        self.buttons = touch.NAME_MAPPING  # Names of the touch buttons

    def runcommand(self, command):
        if command:
            logging.info(f"Running command: {command}")
            process = subprocess.Popen(command, shell=True, stdin=None, stdout=open("/dev/null", "w"), stderr=None,
                                       executable="/bin/bash")
            process.wait()

    def on_loaded(self):
        logging.info("Touch Button plugin loaded.")
        touch.setup()
        logging.info("Testing raw touch functionality.")
        try:
            for i in range(6):
                touch.set_led(i, 1)  # Test LEDs
                time.sleep(0.1)
                touch.set_led(i, 0)
                logging.info(f"LED test for button index {i} complete.")
        except Exception as e:
            logging.error(f"Error testing LEDs: {e}")

        # Initialize touch buttons
        buttons = self.options.get('buttons', {})
        for button_name, actions in buttons.items():
            if button_name in self.buttons:
                button_index = self.buttons.index(button_name)
                short_press_command = actions.get('short_press')
                long_press_command = actions.get('long_press')
                self.register_touch_handler(button_index, button_name, short_press_command, long_press_command)
                logging.info(f"Configured button '{button_name}' with short press: {short_press_command}, long press: {long_press_command}")
            else:
                logging.warning(f"Button '{button_name}' not recognized. Available buttons: {', '.join(self.buttons)}")

    def register_touch_handler(self, button_index, button_name, short_press_command, long_press_command):
        """Register event handlers for touch buttons."""
        def handler(event_obj):
            # logging.debug(f"Handler invoked for event '{event_obj.event}' on button '{button_name}'.")
            self.on_touch_event(button_index, button_name, event_obj, short_press_command, long_press_command)

        touch.on(button_index, handler)
        # logging.info(f"Handler registered for button '{button_name}' (index {button_index}).")

    def on_touch_event(self, button_index, button_name, event_obj, short_press_command, long_press_command):
        """Handle touch events and determine press duration."""
        event_type = event_obj.event  # Extract the event type
        # logging.info(f"Event '{event_type}' detected for button '{button_name}' (index {button_index}).")

        if event_type == 'press':
            self.button_hold_times[button_name] = time.time()
            touch.set_led(button_index, 1)  # Turn LED on when button is pressed
            # logging.debug(f"Button '{button_name}' pressed. LED {button_index} turned on.")
        elif event_type == 'release':
            hold_time = time.time() - self.button_hold_times.get(button_name, 0)
            touch.set_led(button_index, 0)  # Turn LED off when button is released
            # logging.debug(f"Button '{button_name}' released. LED {button_index} turned off.")
            # logging.info(f"Button '{button_name}' released after {hold_time:.2f} seconds.")
            if hold_time >= 1.0:
                logging.info(f"Long press detected on '{button_name}'. Running command: {long_press_command}")
                self.runcommand(long_press_command)
            else:
                logging.info(f"Short press detected on '{button_name}'. Running command: {short_press_command}")
                self.runcommand(short_press_command)


    def on_unload(self, ui):
        logging.info("Touch Button plugin unloaded.")
