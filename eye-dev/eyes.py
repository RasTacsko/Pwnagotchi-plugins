import logging
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
            "address": "0x3D",
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

# Global variable to track and pass on to functions
current_face = "default"
current_offset_x = 0
current_offset_y = 0
current_curious = False

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

def draw_eyes(device, config, face=None, offset_x=None, offset_y=None, curious=None, blink_height_left=None, blink_height_right=None):
    """
    Draw the eyes on the display with optional face-based eyelids.
    :param device: Display device
    :param config: Configuration dictionary
    :param offset_x: Horizontal offset for eye movement (optional, defaults to global current_offset_x)
    :param offset_y: Vertical offset for eye movement (optional, defaults to global current_offset_y)
    :param blink_height_left: Current height of the left eye for blinking
    :param blink_height_right: Current height of the right eye for blinking
    :param face: Optional face parameter to adjust eyelids
    """
    global current_face, current_offset_x, current_offset_y, current_curious  # Use global variables for offsets and face and curious option

    # Default to global offsets if not explicitly provided
    if offset_x is None:
        offset_x = current_offset_x
    if offset_y is None:
        offset_y = current_offset_y

    # Update the current face if a new face is provided
    if face:
        current_face = face
        
    if curious is not None:
        current_curious = curious

    logging.debug(f"Drawing eyes with face: {current_face}, offset_x: {offset_x}, offset_y: {offset_y}")

    # Create a blank image
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

    if current_curious:
        max_increase = 0.4  # Max increase by 30%
        scale_factor = max_increase / (config["screen"]["width"] // 2)
        
        if offset_x < 0:  # Moving left
            eye_width_left += int(scale_factor * abs(offset_x) * left_eye["height"])
            eye_width_right -= int(scale_factor * abs(offset_x) * right_eye["height"])
            eye_height_left += int(scale_factor * abs(offset_x) * left_eye["height"])
            eye_height_right -= int(scale_factor * abs(offset_x) * right_eye["height"])
        elif offset_x > 0:  # Moving right
            eye_height_left -= int(scale_factor * abs(offset_x) * left_eye["height"])
            eye_height_right += int(scale_factor * abs(offset_x) * right_eye["height"])
            eye_width_left -= int(scale_factor * abs(offset_x) * left_eye["height"])
            eye_width_right += int(scale_factor * abs(offset_x) * right_eye["height"])

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

    draw.rounded_rectangle(left_eye_coords, radius=roundness_left, outline=1, fill=1)
    draw.rounded_rectangle(right_eye_coords, radius=roundness_right, outline=1, fill=1)

    # Default eyelid heights
    eyelid_bottom_left_height = 0
    eyelid_bottom_right_height = 0
    eyelid_top_inner_left_height = 0
    eyelid_top_inner_right_height = 0
    eyelid_top_outer_left_height = 0
    eyelid_top_outer_right_height = 0

    # Face-based eyelid adjustments
    if current_face == "happy":
        eyelid_bottom_left_height = eye_height_left // 2
        eyelid_bottom_right_height = eye_height_right // 2
    elif current_face == "angry":
        eyelid_top_inner_left_height = eye_height_left // 2
        eyelid_top_inner_right_height = eye_height_right // 2
    elif current_face == "tired":
        eyelid_top_outer_left_height = eye_height_left // 2
        eyelid_top_outer_right_height = eye_height_right // 2

    # Draw top eyelids
    if eyelid_top_inner_left_height or eyelid_top_outer_left_height > 0:
        draw.polygon([
            (left_eye_coords[0], left_eye_coords[1]), 
            (left_eye_coords[2], left_eye_coords[1]), 
            (left_eye_coords[2], left_eye_coords[1] + eyelid_top_inner_left_height),
            (left_eye_coords[0], left_eye_coords[1] + eyelid_top_outer_left_height),  
        ], fill=0)

    if eyelid_top_inner_right_height or eyelid_top_outer_right_height > 0:
        draw.polygon([
            (right_eye_coords[0], right_eye_coords[1]),  
            (right_eye_coords[2], right_eye_coords[1]),  
            (right_eye_coords[2], right_eye_coords[1] + eyelid_top_outer_right_height),
            (right_eye_coords[0], right_eye_coords[1] + eyelid_top_inner_right_height),  
        ], fill=0)

    # Draw bottom eyelids
    if eyelid_bottom_left_height > 0:
        draw.rounded_rectangle(
            (
                left_eye_coords[0],
                left_eye_coords[3] - eyelid_bottom_left_height,
                left_eye_coords[2],
                left_eye_coords[3],
            ),
            radius=roundness_left,
            outline=0,
            fill=0,
        )

    if eyelid_bottom_right_height > 0:
        draw.rounded_rectangle(
            (
                right_eye_coords[0],
                right_eye_coords[3] - eyelid_bottom_right_height,
                right_eye_coords[2],
                right_eye_coords[3],
            ),
            radius=roundness_right,
            outline=0,
            fill=0,
        )

    device.display(image)

def get_constraints(config, device):
    """
    Calculate the movement constraints for the eyes to ensure they stay on the screen.

    :param config: Configuration dictionary
    :param device: Display device
    :return: A tuple of (min_x_offset, max_x_offset, min_y_offset, max_y_offset)
    """
    left_eye = config["eye"]["left"]
    right_eye = config["eye"]["right"]
    distance = config["eye"]["distance"]

    # Screen dimensions
    screen_width = device.width
    screen_height = device.height

    # Calculate horizontal constraints
    # Minimum X is based on left eye's width, distance, and screen boundaries
    min_x_offset = -(screen_width // 2 - distance // 2 - left_eye["width"])
    # Maximum X is based on right eye's width, distance, and screen boundaries
    max_x_offset = screen_width // 2 - distance // 2 - right_eye["width"]

    # Calculate vertical constraints
    # Minimum and maximum Y constraints ensure the eyes do not go off the top or bottom of the screen
    min_y_offset = -(screen_height // 2 - max(left_eye["height"], right_eye["height"]) // 2)
    max_y_offset = screen_height // 2 - max(left_eye["height"], right_eye["height"]) // 2

    logging.debug(
        f"Constraints calculated: min_x_offset={min_x_offset}, max_x_offset={max_x_offset}, "
        f"min_y_offset={min_y_offset}, max_y_offset={max_y_offset}"
    )

    return min_x_offset, max_x_offset, min_y_offset, max_y_offset

def look(device, config, direction="C", speed="fast", curious=None):
    """
    Move the eyes to a specific position on the screen based on the cardinal direction.
    """
    global current_face, current_offset_x, current_offset_y, current_curious  # Track offsets globally
    logging.info(f"Starting look animation towards {direction} at {speed} speed with face: {current_face}")

    # Get movement constraints
    min_x_offset, max_x_offset, min_y_offset, max_y_offset = get_constraints(config, device)
        
    fps = config["render"].get("fps", 30)
    interval = 1 / fps  # Time per frame
    
    # Determine target offsets based on direction
    if direction == "L":  # Left
        target_offset_x = min_x_offset
        target_offset_y = 0
    elif direction == "R":  # Right
        target_offset_x = max_x_offset
        target_offset_y = 0
    elif direction == "T":  # Top
        target_offset_x = 0
        target_offset_y = min_y_offset
    elif direction == "B":  # Bottom
        target_offset_x = 0
        target_offset_y = max_y_offset
    elif direction == "TL":  # Top-left
        target_offset_x = min_x_offset
        target_offset_y = min_y_offset
    elif direction == "TR":  # Top-right
        target_offset_x = max_x_offset
        target_offset_y = min_y_offset
    elif direction == "BL":  # Bottom-left
        target_offset_x = min_x_offset
        target_offset_y = max_y_offset
    elif direction == "BR":  # Bottom-right
        target_offset_x = max_x_offset
        target_offset_y = max_y_offset
    else:  # Center
        target_offset_x = 0
        target_offset_y = 0

    # Movement speed settings
    if speed == "fast":
        movement_speed = 6
    elif speed == "medium":
        movement_speed = 4
    else:  # Default to "slow"
        movement_speed = 1

    # Movement loop
    while current_offset_x != target_offset_x or current_offset_y != target_offset_y:
        # Adjust X offsets
        if current_offset_x < target_offset_x:
            current_offset_x = min(current_offset_x + movement_speed, target_offset_x)
        elif current_offset_x > target_offset_x:
            current_offset_x = max(current_offset_x - movement_speed, target_offset_x)

        # Adjust Y offsets
        if current_offset_y < target_offset_y:
            current_offset_y = min(current_offset_y + movement_speed, target_offset_y)
        elif current_offset_y > target_offset_y:
            current_offset_y = max(current_offset_y - movement_speed, target_offset_y)

        # Draw the eyes at the current position
        draw_eyes(
            device,
            config,
            offset_x=current_offset_x,
            offset_y=current_offset_y,
            face=current_face,
        )

        # Wait for the next frame based on FPS
        time.sleep(interval)

    logging.info(f"Look animation towards {direction} complete.")

def blink(device, config, eye="both", speed="fast", curious=None):
    """
    Perform a blinking animation for one or both eyes while maintaining the current face and offsets.
    """
    global current_face, current_offset_x, current_offset_y, current_curious  # Use global offsets and face
    logging.info(f"Starting blinking animation for {eye} eye(s) at {speed} speed with face: {current_face}")

    # Blinking variables
    left_eye_height_orig = config["eye"]["left"]["height"]
    right_eye_height_orig = config["eye"]["right"]["height"]
    blink_height_left = left_eye_height_orig
    blink_height_right = right_eye_height_orig
    blink_direction = -1  # -1 to shrink (closing), 1 to grow (opening)
    fps = config["render"].get("fps", 30)
    interval = 1 / fps  # Time per frame

    # Speed settings
    if speed == "fast":
        blink_steps = 5
    elif speed == "medium":
        blink_steps = 10
    else:  # Default to "slow"
        blink_steps = 15

    blink_step_left = (left_eye_height_orig - 2) / blink_steps
    blink_step_right = (right_eye_height_orig - 2) / blink_steps

    for _ in range(blink_steps * 2):  # Two phases: closing and opening
        if eye in ["both", "left"]:  # Blink left eye
            blink_height_left += blink_direction * blink_step_left
            blink_height_left = max(2, min(blink_height_left, left_eye_height_orig))

        if eye in ["both", "right"]:  # Blink right eye
            blink_height_right += blink_direction * blink_step_right
            blink_height_right = max(2, min(blink_height_right, right_eye_height_orig))

        # Switch directions after closing
        if blink_direction == -1 and (
            (eye in ["both", "left"] and blink_height_left <= 2) or
            (eye in ["both", "right"] and blink_height_right <= 2)
        ):
            blink_direction = 1  # Start opening phase

        # Draw the current frame
        draw_eyes(
            device,
            config,
            offset_x=current_offset_x,
            offset_y=current_offset_y,
            blink_height_left=blink_height_left if eye in ["both", "left"] else None,
            blink_height_right=blink_height_right if eye in ["both", "right"] else None,
            face=current_face,
        )

        time.sleep(interval)

    logging.info(f"Blink animation for {eye} eye(s) complete.")
    
def main():
    # Load screen and render configurations
    screen_config = load_config("screenconfig.toml", DEFAULT_SCREEN_CONFIG)
    render_config = load_config("eyeconfig.toml", DEFAULT_RENDER_CONFIG)

    # Merge configurations
    config = {**screen_config, **render_config}

    # Initialize the display device
    device = get_device(config)

    # Main loop to test look functionality
    draw_eyes(device, config, face="angry", curious=True)
    time.sleep(1)

    look(device, config, direction="L", speed="medium")  # Look left slowly
    # blink(device, config, speed="medium")
    time.sleep(1)

    look(device, config, direction="R", speed="medium")  # Look top-right at medium speed
    # blink(device, config, speed="medium")
    time.sleep(1)

    look(device, config, direction="C", speed="medium")  # Look top-right at medium speed
    blink(device, config, speed="fast")
    time.sleep(1)

    draw_eyes(device, config, face="tired")
    time.sleep(1)

    look(device, config, direction="TL", speed="medium")  # Look left slowly
    # blink(device, config, speed="medium", eye="left")
    time.sleep(1)

    look(device, config, direction="TR", speed="medium")  # Look top-right at medium speed
    # blink(device, config, speed="medium", eye="right")
    time.sleep(1)

    look(device, config, direction="T", speed="medium")  # Look top-right at medium speed
    # blink(device, config, speed="medium", eye="both")
    time.sleep(1)

    draw_eyes(device, config, face="happy")
    time.sleep(1)

if __name__ == "__main__":
    main()