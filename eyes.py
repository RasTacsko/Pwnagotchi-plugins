import logging
import random
import time
import signal
import sys
import toml
from PIL import Image, ImageDraw
from luma.core.interface.serial import i2c, spi
from luma.oled.device import ssd1306
from luma.lcd.device import ili9341

# Enable debug logging
logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s - %(levelname)s - %(message)s",
)

# Load configuration from a TOML file
def load_config(file_path):
    """
    Load the configuration from a TOML file.

    :param file_path: Path to the configuration file
    :return: Configuration dictionary
    """
    logging.info(f"Loading configuration from {file_path}...")
    try:
        config = toml.load(file_path)
        logging.info("Configuration loaded successfully!")
        return config
    except Exception as e:
        logging.error(f"Error loading configuration: {e}")
        sys.exit(1)

# Initialize the display based on the configuration
def init_screen(config):
    """
    Initialize the display device based on the configuration.

    :param config: Configuration dictionary
    :return: Initialized display device
    """
    try:
        screen_type = config["screen"]["type"]
        driver = config["screen"]["driver"]
        width = config["screen"]["width"]
        height = config["screen"]["height"]
        connection = config["screen"]["connection"]

        if connection == "i2c":
            i2c_address = int(config["screen"]["i2c"]["address"], 16)
            serial = i2c(port=1, address=i2c_address)
        elif connection == "spi":
            spi_params = config["screen"]["spi"]
            serial = spi(
                port=0,
                device=0,
                gpio_DC=spi_params["ds"],
                gpio_RST=spi_params.get("reset", None),
                gpio_backlight=spi_params.get("bl", None),
            )
        else:
            raise ValueError("Unsupported connection type!")

        # Initialize device based on driver
        if driver == "ssd1306":
            device = ssd1306(serial, width=width, height=height)
        elif driver == "ili9341":
            device = ili9341(serial, width=width, height=height)
        else:
            raise ValueError("Unsupported driver!")

        logging.info(f"Initialized {screen_type} screen with {driver} driver.")
        return device
    except Exception as e:
        logging.error(f"Error initializing screen: {e}")
        sys.exit(1)

# Draw the eyes on the screen
def draw_eyes(device, config, offset_x=0, offset_y=0, blink_height_left=None, blink_height_right=None):
    """
    Draw the eyes on the display.

    :param device: Display device
    :param config: Configuration dictionary
    :param offset_x: Horizontal offset for eye movement
    :param offset_y: Vertical offset for eye movement
    :param blink_height_left: Current height of the left eye for blinking
    :param blink_height_right: Current height of the right eye for blinking
    """
    image = Image.new("1", (device.width, device.height), "black")
    draw = ImageDraw.Draw(image)

    # Left eye configuration
    left_eye = config["eye"]["left"]
    eye_width_left = left_eye["width"]
    eye_height_left = blink_height_left or left_eye["height"]
    roundness_left = left_eye["roundness"]

    # Right eye configuration
    right_eye = config["eye"]["right"]
    eye_width_right = right_eye["width"]
    eye_height_right = blink_height_right or right_eye["height"]
    roundness_right = right_eye["roundness"]

    distance = config["eye"]["distance"]

    # Calculate eye coordinates
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

    # Draw the eyes
    draw.rounded_rectangle(left_eye_coords, radius=roundness_left, outline=1, fill=1)
    draw.rounded_rectangle(right_eye_coords, radius=roundness_right, outline=1, fill=1)

    # Display the image
    device.display(image)

# Idle animation with smooth movement and blinking
def on_idle(device, config):
    """
    Animate the eyes with idle movement and blinking.

    :param device: Display device
    :param config: Configuration dictionary
    """
    current_offset_x = 0
    current_offset_y = 0
    target_offset_x = 0
    target_offset_y = 0

    left_eye_height_orig = config["eye"]["left"]["height"]
    right_eye_height_orig = config["eye"]["right"]["height"]

    blink_height_left = left_eye_height_orig
    blink_height_right = right_eye_height_orig
    blink_direction = -1
    blinking = False

    IDLE_OFFSET_RANGE = 10
    MOVEMENT_SPEED = 1
    BLINK_SPEED = 2
    FPS = 30

    while True:
        # Smooth idle movement
        if current_offset_x == target_offset_x and current_offset_y == target_offset_y:
            target_offset_x = random.randint(-IDLE_OFFSET_RANGE, IDLE_OFFSET_RANGE)
            target_offset_y = random.randint(-IDLE_OFFSET_RANGE, IDLE_OFFSET_RANGE)

        current_offset_x += (MOVEMENT_SPEED if current_offset_x < target_offset_x else -MOVEMENT_SPEED) if current_offset_x != target_offset_x else 0
        current_offset_y += (MOVEMENT_SPEED if current_offset_y < target_offset_y else -MOVEMENT_SPEED) if current_offset_y != target_offset_y else 0

        # Smooth blinking
        if blinking:
            blink_height_left += blink_direction * BLINK_SPEED * (left_eye_height_orig / right_eye_height_orig)
            blink_height_right += blink_direction * BLINK_SPEED
            if blink_height_left <= 2 or blink_height_right <= 2:
                blink_direction = 1
            elif blink_height_left >= left_eye_height_orig and blink_height_right >= right_eye_height_orig:
                blinking = False
                blink_height_left = left_eye_height_orig
                blink_height_right = right_eye_height_orig
        elif random.random() < 0.01:  # Random chance to blink
            logging.info("Blinking triggered!")
            blinking = True
            blink_direction = -1

        # Draw eyes
        draw_eyes(device, config, current_offset_x, current_offset_y, blink_height_left, blink_height_right)

        # Maintain 30 FPS
        time.sleep(1 / FPS)

# Main function
if __name__ == "__main__":
    config = load_config("eyeconfig.toml")
    device = init_screen(config)

    def signal_handler(sig, frame):
        logging.info("Exiting...")
        device.clear()
        sys.exit(0)

    signal.signal(signal.SIGINT, signal_handler)

    draw_eyes(device, config)  # Initial Draw
    on_idle(device, config)
