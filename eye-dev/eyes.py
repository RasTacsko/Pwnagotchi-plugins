import logging
import signal
import sys
import toml
import random
import time
from PIL import Image, ImageDraw
from luma.core.interface.serial import i2c, spi
import luma.oled.device as oled
import luma.lcd.device as lcd

# Enable debug logging
logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s - %(levelname)s - %(message)s",
)

# Default configuration for the OLED screen
DEFAULT_SCREEN_CONFIG = {
    "screen": {
        "type": "oled",
        "driver": "ssd1306",
        "width": 128,
        "height": 64,
        "rotate": 0,
        "interface": "i2c",
        "i2c": {
            "address": "0x3C",
            "i2c_port": 1,
        },
    }
}

# Default rendering parameters
DEFAULT_RENDER_CONFIG = {
    "render": {
        "fps": 30,  # Default refresh rate
    },
    "eye": {
        "distance": 10,  # Default distance between eyes
        "left": {
            "width": 36,
            "height": 36,
            "roundness": 8,
        },
        "right": {
            "width": 36,
            "height": 36,
            "roundness": 8,
        },
    },
}

def load_config(file_path, default_config):
    """
    Load configuration from a TOML file. If the file is missing, use the default configuration.

    :param file_path: Path to the TOML file
    :param default_config: Default configuration dictionary
    :return: Loaded configuration dictionary
    """
    try:
        with open(file_path, "r") as f:
            logging.info(f"Loading configuration from {file_path}...")
            config = toml.load(f)
            logging.info(f"Configuration loaded successfully from {file_path}.")
            return {**default_config, **config}  # Merge defaults with loaded config
    except FileNotFoundError:
        logging.warning(f"{file_path} not found. Using default configuration.")
        return default_config
    except Exception as e:
        logging.error(f"Error reading configuration from {file_path}: {e}")
        sys.exit(1)

def validate_screen_config(config):
    """
    Validate the screen configuration to ensure required fields are present.

    :param config: Screen configuration dictionary
    """
    try:
        screen = config["screen"]
        required_fields = ["type", "driver", "width", "height", "interface"]

        for field in required_fields:
            if field not in screen:
                raise ValueError(f"Missing required field: '{field}' in screen configuration.")

        if screen["interface"] == "i2c" and "i2c" not in screen:
            raise ValueError("Missing 'i2c' section for I2C interface.")
        if screen["interface"] == "spi" and "spi" not in screen:
            raise ValueError("Missing 'spi' section for SPI interface.")
    except KeyError as e:
        logging.error(f"Configuration validation error: Missing key {e}")
        sys.exit(1)
    except ValueError as e:
        logging.error(f"Configuration validation error: {e}")
        sys.exit(1)

def get_device(config):
    """
    Create and initialize the display device based on the configuration.

    :param config: Screen configuration dictionary
    :return: Initialized display device
    """
    try:
        screen = config["screen"]
        validate_screen_config(config)

        # Create the serial interface
        serial = None  # Initialize serial variable
        if screen["interface"] == "i2c":
            i2c_address = int(screen["i2c"]["address"], 16)
            serial = i2c(port=screen["i2c"].get("i2c_port", 1), address=i2c_address)
        elif screen["interface"] == "spi":
            spi_params = screen["spi"]
            gpio_params = screen.get("gpio", {})
            serial = spi(
                port=spi_params.get("spi_port", 0),
                device=spi_params.get("spi_device", 0),
                gpio_DC=gpio_params.get("gpio_data_command"),
                gpio_RST=gpio_params.get("gpio_reset"),
                gpio_backlight=gpio_params.get("gpio_backlight"),
                bus_speed_hz=spi_params.get("spi_bus_speed", 8000000),
            )
        else:
            raise ValueError(f"Unsupported interface type: {screen['interface']}")

        # Dynamically load the driver
        driver_name = screen["driver"]
        driver_module = getattr(oled, driver_name, None) or getattr(lcd, driver_name, None)

        if driver_module is None:
            raise ValueError(f"Unsupported driver: {driver_name}")

        # Initialize the device
        device = driver_module(serial, width=screen["width"], height=screen["height"], rotate=screen.get("rotate", 0))

        logging.info(f"Initialized {screen['type']} screen with driver {driver_name}.")
        return device
    except ValueError as e:
        logging.error(f"Configuration error: {e}")
        sys.exit(1)
    except Exception as e:
        logging.error(f"Error initializing screen: {e}")
        sys.exit(1)

def draw_eyes(device, config, offset_x=0, offset_y=0, blink_height_left=None, blink_height_right=None, mood=None):
    """
    Draw the eyes on the display with optional mood-based eyelids.

    :param device: Display device
    :param config: Configuration dictionary
    :param offset_x: Horizontal offset for eye movement
    :param offset_y: Vertical offset for eye movement
    :param blink_height_left: Current height of the left eye for blinking
    :param blink_height_right: Current height of the right eye for blinking
    :param mood: Optional mood parameter to adjust eyelids
    """
    logging.debug("Drawing eyes on the display...")
    
    # Create a blank image with the correct mode ("1" for ssd1306)
    image = Image.new(device.mode, (device.width, device.height), "black")
    draw = ImageDraw.Draw(image)

    left_eye = config["eye"]["left"]
    eye_width_left = left_eye["width"]
    eye_height_left = blink_height_left or left_eye["height"]
    roundness_left = left_eye["roundness"]

    right_eye = config["eye"]["right"]
    eye_width_right = right_eye["width"]
    eye_height_right = blink_height_right or right_eye["height"]
    roundness_right = right_eye["roundness"]

    distance = config["eye"]["distance"]

    # Calculate eye positions
    left_eye_coords = (
        device.width // 2 - eye_width_left - distance // 2 + offset_x,
        device.height // 2 - eye_height_left // 2 + offset_y,
        device.width // 2 - distance // 2 + offset_x,
        device.height // 2 + eye_height_left // 2 + offset_y,
    )
    right_eye_coords = (
        device.width // 2 + distance // 2 + offset_x,
        device.height // 2 - eye_height_right // 2 + offset_y,
        device.width // 2 + eye_width_right + distance // 2 + offset_x,
        device.height // 2 + eye_height_right // 2 + offset_y,
    )

    # Draw the basic eye shapes
    draw.rounded_rectangle(left_eye_coords, radius=roundness_left, outline=1, fill=1)
    draw.rounded_rectangle(right_eye_coords, radius=roundness_right, outline=1, fill=1)

    # Overlay mood-based eyelids
    if mood == "tired":
        eyelids_tired_height = eye_height_left // 2
        draw.polygon([
            (left_eye_coords[0], left_eye_coords[1]),  # Top-left
            (left_eye_coords[2], left_eye_coords[1]),  # Top-right
            (left_eye_coords[0], left_eye_coords[1] + eyelids_tired_height),  # Bottom-left
        ], fill=0)
        draw.polygon([
            (right_eye_coords[0], right_eye_coords[1]),  # Top-left
            (right_eye_coords[2], right_eye_coords[1]),  # Top-right
            (right_eye_coords[2], right_eye_coords[1] + eyelids_tired_height),  # Bottom-right
        ], fill=0)

    elif mood == "angry":
        eyelids_angry_height = eye_height_left // 2
        draw.polygon([
            (left_eye_coords[0], left_eye_coords[1]),  # Top-left
            (left_eye_coords[2], left_eye_coords[1]),  # Top-right
            (left_eye_coords[2], left_eye_coords[1] + eyelids_angry_height),  # Bottom-right
        ], fill=0)
        draw.polygon([
            (right_eye_coords[0], right_eye_coords[1]),  # Top-left
            (right_eye_coords[2], right_eye_coords[1]),  # Top-right
            (right_eye_coords[0], right_eye_coords[1] + eyelids_angry_height),  # Bottom-left
        ], fill=0)

    elif mood == "happy":
        eyelids_happy_offset = eye_height_left // 2
        draw.rounded_rectangle(
            (
                left_eye_coords[0],
                left_eye_coords[3] - eyelids_happy_offset,
                left_eye_coords[2],
                left_eye_coords[3],
            ),
            radius=roundness_left,
            outline=0,
            fill=0
        )
        draw.rounded_rectangle(
            (
                right_eye_coords[0],
                right_eye_coords[3] - eyelids_happy_offset,
                right_eye_coords[2],
                right_eye_coords[3],
            ),
            radius=roundness_right,
            outline=0,
            fill=0
        )

    # Display the image
    device.display(image)

def on_idle(device, config):
    """
    Animate the eyes with idle movement and blinking.

    :param device: Display device
    :param config: Configuration dictionary
    """
    moods = ["happy", "angry", "tired", None]  # None represents the default mood
    mood_index = 0
    
    fps = config["render"].get("fps", 30)  # Use configured FPS or fallback to default
    interval = 1 / fps  # Calculate time per frame

    # Idle movement variables
    current_offset_x = 0
    current_offset_y = 0
    target_offset_x = 0
    target_offset_y = 0
    IDLE_OFFSET_RANGE = 10
    MOVEMENT_SPEED = 1

    # Blinking variables
    left_eye_height_orig = config["eye"]["left"]["height"]
    right_eye_height_orig = config["eye"]["right"]["height"]
    blink_height_left = left_eye_height_orig
    blink_height_right = right_eye_height_orig
    blink_direction = -1  # -1 to shrink, 1 to grow
    blinking = False

    while True:
        logging.debug("Idle animation loop running...")

        # Smooth idle movement
        if current_offset_x == target_offset_x and current_offset_y == target_offset_y:
            target_offset_x = random.randint(-IDLE_OFFSET_RANGE, IDLE_OFFSET_RANGE)
            target_offset_y = random.randint(-IDLE_OFFSET_RANGE, IDLE_OFFSET_RANGE)
            logging.debug(f"New idle target: ({target_offset_x}, {target_offset_y})")

        if current_offset_x < target_offset_x:
            current_offset_x += MOVEMENT_SPEED
        elif current_offset_x > target_offset_x:
            current_offset_x -= MOVEMENT_SPEED

        if current_offset_y < target_offset_y:
            current_offset_y += MOVEMENT_SPEED
        elif current_offset_y > target_offset_y:
            current_offset_y -= MOVEMENT_SPEED

        # Smooth blinking
        if blinking:
            blink_height_left += blink_direction * 10  # Adjust speed as needed
            blink_height_right += blink_direction * 10

            if blink_height_left <= 2 or blink_height_right <= 2:  # Fully closed
                logging.info("Eyes fully closed, starting to open...")
                blink_direction = 1  # Start opening
            elif blink_height_left >= left_eye_height_orig and blink_height_right >= right_eye_height_orig:  # Fully opened
                logging.info("Blinking complete.")
                blinking = False  # End blinking
                blink_height_left = left_eye_height_orig
                blink_height_right = right_eye_height_orig
        elif random.random() < 0.1:  # Random chance to start blinking
            logging.info("Blinking triggered!")
            blinking = True
            blink_direction = -1  # Start shrinking
            
        # current_mood = moods[mood_index]
        # logging.info(f"Switching to mood: {current_mood or 'default'}")
        # draw_eyes(device, config, mood=current_mood)  # Pass the mood to draw_eyes
        # mood_index = (mood_index + 1) % len(moods)  # Cycle through moods
        # time.sleep(3)  # Wait for 3 seconds

        # Draw eyes with current state
        draw_eyes(device, config, current_offset_x, current_offset_y, blink_height_left, blink_height_right)

        # Wait to maintain 30 FPS
        time.sleep(interval)

# def test_draw(device, config):
    # """
    # Test rendering a static frame to ensure the screen works.
    # """
    # logging.info("Testing static draw...")
    # draw_eyes(device, config)
    # time.sleep(5)  # Keep the image on screen for 5 seconds

def interpolate(value_from, value_to, step, total_steps):
    """
    Linearly interpolate between two values.
    
    :param value_from: Starting value
    :param value_to: Target value
    :param step: Current step in the transition
    :param total_steps: Total number of steps in the transition
    :return: Interpolated value
    """
    return value_from + (value_to - value_from) * (step / total_steps)

def set_mood_with_transition(device, config, current_eye_config, target_mood, transition_speed):
    """
    Smoothly transition the eye shapes and eyelids to the target mood.

    :param device: Display device
    :param config: Configuration dictionary.
    :param current_eye_config: Current eye configuration (unused for now).
    :param target_mood: Target mood name (e.g., "happy", "angry").
    :param transition_speed: Number of frames for the transition.
    """
    if "moods" not in config or target_mood not in config["moods"]:
        logging.warning(f"Mood '{target_mood}' not found in the configuration. Using default eye shapes.")
        return current_eye_config  # No changes

    target_mood_config = config["moods"][target_mood]
    logging.info(f"Transitioning to mood: {target_mood}")

    # Perform smooth transition
    for step in range(transition_speed + 1):
        draw_eyes(
            device,
            eye_config=config["eye"],
            eyelid_config=target_mood_config["eyelids"],
            mood=target_mood,
            step=step,
            total_steps=transition_speed,
        )
        time.sleep(1 / config["render"]["fps"])

    return target_mood_config

def moodtest(device, config):
    """
    Test different moods by switching the eye shapes every 5 seconds.

    :param device: Display device
    :param config: Configuration dictionary
    """
    moods = ["happy", "angry", "tired", None]  # None represents the default mood
    mood_index = 0

    while True:
        current_mood = moods[mood_index]
        logging.info(f"Switching to mood: {current_mood or 'default'}")
        draw_eyes(device, config, mood=current_mood)  # Pass the mood to draw_eyes
        mood_index = (mood_index + 1) % len(moods)  # Cycle through moods
        time.sleep(3)  # Wait for 5 seconds

def main():
    # Load screen and render configurations
    screen_config = load_config("screenconfig.toml", DEFAULT_SCREEN_CONFIG)
    render_config = load_config("eyeconfig.toml", DEFAULT_RENDER_CONFIG)

    # Merge configurations
    config = {**screen_config, **render_config}

    # Initialize the display device
    device = get_device(config)

    # Display initial state
    # draw_eyes(device, config)
    # test_draw(device, config)

    # Start idle animation
    on_idle(device, config)

    # Start the mood test
    # moodtest(device, config)

if __name__ == "__main__":
    main()