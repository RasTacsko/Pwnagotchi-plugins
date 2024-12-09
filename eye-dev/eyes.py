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

# Global variable to track and pass on to functions
current_face = "default"
current_offset_x = 0
current_offset_y = 0
current_curious = False
current_closed = False

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

def draw_eyes(device, config, offset_x=None, offset_y=None, blink_height_left=None, blink_height_right=None, 
              face=None, curious=None, command=None, target_offset_x=None, target_offset_y=None, speed="medium", eye="both", closed=None):
    """
    Draw the eyes on the display with optional face-based eyelids and support for curious mode.

    :param device: Display device
    :param config: Configuration dictionary
    :param offset_x: Horizontal offset for eye movement (optional, defaults to global current_offset_x)
    :param offset_y: Vertical offset for eye movement (optional, defaults to global current_offset_y)
    :param blink_height_left: Current height of the left eye for blinking
    :param blink_height_right: Current height of the right eye for blinking
    :param face: Optional face parameter to adjust eyelids
    :param curious: If True, adjust eye sizes based on position
    :param command: Command to execute ("look", "blink", or None)
    :param target_offset_x: Target horizontal offset for look animations
    :param target_offset_y: Target vertical offset for look animations
    :param speed: Speed of animation ("fast", "medium", "slow")
    :param eye: Specify which eye to blink ("left", "right", or "both")
    """
    global current_face, current_offset_x, current_offset_y, current_curious, current_closed  # Use global variables for state

    # Default to global offsets if not explicitly provided
    if offset_x is None:
        offset_x = current_offset_x
    if offset_y is None:
        offset_y = current_offset_y

    # Default to global face and curious state if not explicitly provided
    if face is None:
        face = current_face
    else:
        current_face = face  # Update global face state
        
    if curious is None:
        curious = current_curious
    else:
        current_curious = curious  # Update global curious state
        
    if closed is None:
        closed = current_closed
    else:
        current_closed = closed  # Update global closed state

    logging.debug(f"Drawing eyes with face: {face}, offset_x: {offset_x}, offset_y: {offset_y}, curious={curious}, command={command}")

    # Create a blank image
    image = Image.new(device.mode, (device.width, device.height), "black")
    draw = ImageDraw.Draw(image)

    # Eye parameters
    left_eye = config["eye"]["left"]
    right_eye = config["eye"]["right"]
    distance = config["eye"]["distance"]

    # Base dimensions for eyes
    eye_width_left = left_eye["width"]
    eye_width_right = right_eye["width"]
    eye_height_left = blink_height_left if blink_height_left is not None else left_eye["height"]
    eye_height_right = blink_height_right if blink_height_right is not None else right_eye["height"]

    # Apply curious effect dynamically
    if curious:
        max_increase = 0.4  # Max increase by 40%
        scale_factor = max_increase / (config["screen"]["width"] // 2)
        if offset_x < 0:  # Moving left
            eye_width_left += int(scale_factor * abs(offset_x) * left_eye["width"])
            eye_width_right -= int(scale_factor * abs(offset_x) * right_eye["width"])
            eye_height_left += int(scale_factor * abs(offset_x) * eye_height_left)
            eye_height_right -= int(scale_factor * abs(offset_x) * eye_height_right)
        elif offset_x > 0:  # Moving right
            eye_height_left -= int(scale_factor * abs(offset_x) * eye_height_left)
            eye_height_right += int(scale_factor * abs(offset_x) * eye_height_right)
            eye_width_left -= int(scale_factor * abs(offset_x) * left_eye["width"])
            eye_width_right += int(scale_factor * abs(offset_x) * right_eye["width"])

    # Clamp sizes to ensure no negative or unrealistic dimensions
    eye_height_left = max(2, eye_height_left)
    eye_height_right = max(2, eye_height_right)
    eye_width_left = max(2, eye_width_left)
    eye_width_right = max(2, eye_width_right)

    roundness_left = left_eye["roundness"]
    roundness_right = right_eye["roundness"]

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

    # Handle look animations
    if command == "look" and target_offset_x is not None and target_offset_y is not None:
        movement_speed = {"fast": 8, "medium": 4, "slow": 2}.get(speed, 4)
        while current_offset_x != target_offset_x or current_offset_y != target_offset_y:
            if current_offset_x < target_offset_x:
                current_offset_x = min(current_offset_x + movement_speed, target_offset_x)
            elif current_offset_x > target_offset_x:
                current_offset_x = max(current_offset_x - movement_speed, target_offset_x)

            if current_offset_y < target_offset_y:
                current_offset_y = min(current_offset_y + movement_speed, target_offset_y)
            elif current_offset_y > target_offset_y:
                current_offset_y = max(current_offset_y - movement_speed, target_offset_y)

            draw_eyes(device, config, offset_x=current_offset_x, offset_y=current_offset_y, face=current_face, curious=curious, closed=current_closed)
            # time.sleep(1 / config["render"].get("fps", 30))

    # Handle blinking
    if command == "blink":
        left_eye_height_orig = config["eye"]["left"]["height"]
        right_eye_height_orig = config["eye"]["right"]["height"]

        # Default blink heights to original values if None
        if blink_height_left is None:
            blink_height_left = left_eye_height_orig
        if blink_height_right is None:
            blink_height_right = right_eye_height_orig

        # Define the speed of animation in pixels per frame
        movement_speed = {"fast": 12, "medium": 8, "slow": 4}.get(speed, 4)

        blink_direction = -1  # Closing phase initially
        while True:
            if blink_direction == -1:  # Closing phase
                # Adjust left eye height
                if eye in ["both", "left"]:
                    blink_height_left = max(1, blink_height_left - movement_speed)
                # Adjust right eye height
                if eye in ["both", "right"]:
                    blink_height_right = max(1, blink_height_right - movement_speed)

                # Check if both eyes are fully closed
                if (
                    (eye in ["both", "left"] and blink_height_left <= 1) and
                    (eye in ["both", "right"] and blink_height_right <= 1)
                ):
                    blink_direction = 1  # Start opening phase

                # If only one eye is blinking, start opening when it is fully closed
                if eye == "left" and blink_height_left <= 1:
                    blink_direction = 1
                if eye == "right" and blink_height_right <= 1:
                    blink_direction = 1

            elif blink_direction == 1:  # Opening phase
                # Adjust left eye height
                if eye in ["both", "left"]:
                    blink_height_left += movement_speed
                    if blink_height_left >= left_eye_height_orig:
                        blink_height_left = left_eye_height_orig  # Final adjustment
                # Adjust right eye height
                if eye in ["both", "right"]:
                    blink_height_right += movement_speed
                    if blink_height_right >= right_eye_height_orig:
                        blink_height_right = right_eye_height_orig  # Final adjustment

                # Check if both eyes are fully open
                if (
                    (eye in ["both", "left"] and blink_height_left >= left_eye_height_orig) and
                    (eye in ["both", "right"] and blink_height_right >= right_eye_height_orig)
                ):
                    break

                # If only one eye is blinking, stop when it is fully open
                if eye == "left" and blink_height_left >= left_eye_height_orig:
                    break
                if eye == "right" and blink_height_right >= right_eye_height_orig:
                    break

            # Draw the current frame of the blink
            draw_eyes(
                device,
                config,
                offset_x=current_offset_x,
                offset_y=current_offset_y,
                blink_height_left=blink_height_left if eye in ["both", "left"] else None,
                blink_height_right=blink_height_right if eye in ["both", "right"] else None,
                face=current_face,
                curious=curious,
            )
            # time.sleep(1 / config["render"].get("fps", 30))

        # Final frame to ensure eyes are drawn at their original height
        draw_eyes(
            device,
            config,
            offset_x=current_offset_x,
            offset_y=current_offset_y,
            blink_height_left=left_eye_height_orig,
            blink_height_right=right_eye_height_orig,
            face=current_face,
            curious=curious,
        )

    # Handle eye closing
    if command == "close":
        if current_closed:  # If eyes are already closed, no need to animate
            return
        # Default blink heights to original values if None
        left_eye_height_orig = config["eye"]["left"]["height"]
        right_eye_height_orig = config["eye"]["right"]["height"]
        if blink_height_left is None:
            blink_height_left = left_eye_height_orig
        if blink_height_right is None:
            blink_height_right = right_eye_height_orig

        # Define the speed of animation in pixels per frame
        movement_speed = {"fast": 12, "medium": 8, "slow": 4}.get(speed, 4)
        while True:
            if eye in ["both", "left"]:
                blink_height_left = max(1, blink_height_left - movement_speed)
            if eye in ["both", "right"]:
                blink_height_right = max(1, blink_height_right - movement_speed)

            # Draw the current frame of the close animation
            draw_eyes(
                device,
                config,
                offset_x=current_offset_x,
                offset_y=current_offset_y,
                blink_height_left=blink_height_left,
                blink_height_right=blink_height_right,
                face=current_face,
                curious=curious,
            )

            # Break when the eyes are fully closed
            if (blink_height_left <= 1 and eye in ["both", "left"]) and (
                blink_height_right <= 1 and eye in ["both", "right"]
            ):
                current_closed = True  # Update state to closed
                break

    # Handle eye opening
    elif command == "open":
        if not current_closed:  # If eyes are already closed, no need to animate
            return
        # Default blink heights to original values if None
        left_eye_height_orig = config["eye"]["left"]["height"]
        right_eye_height_orig = config["eye"]["right"]["height"]

        if blink_height_left is None:
            blink_height_left = 0  # Start from closed if opening
        if blink_height_right is None:
            blink_height_right = 0  # Start from closed if opening

        # Define the speed of animation in pixels per frame
        movement_speed = {"fast": 12, "medium": 8, "slow": 4}.get(speed, 4)

        while True:
            # Increment eye heights
            if eye in ["both", "left"]:
                blink_height_left += movement_speed
                if blink_height_left >= left_eye_height_orig:
                    blink_height_left = left_eye_height_orig  # Final adjustment
            if eye in ["both", "right"]:
                blink_height_right += movement_speed
                if blink_height_right >= right_eye_height_orig:
                    blink_height_right = right_eye_height_orig  # Final adjustment

            # Draw the current frame
            draw_eyes(
                device,
                config,
                offset_x=current_offset_x,
                offset_y=current_offset_y,
                blink_height_left=blink_height_left,
                blink_height_right=blink_height_right,
                face=current_face,
                curious=current_curious,
                command=None,
            )

            # Exit when both eyes are fully open
            if (
                (blink_height_left >= left_eye_height_orig and eye in ["both", "left"])
                and (blink_height_right >= right_eye_height_orig and eye in ["both", "right"])
            ):
                break

        # Update global eye_close state
        current_closed = False

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

def look(device, config, direction="C", speed="fast", face=None, curious=None, closed=None):
    """
    Move the eyes to a specific position on the screen based on the cardinal direction, with optional face and curious mode.

    :param device: Display device
    :param config: Configuration dictionary
    :param direction: Direction to move the eyes ("C", "L", "R", "T", "B", etc.)
    :param speed: Speed of movement ("fast", "medium", "slow")
    :param face: Optional face parameter to change during the animation
    :param curious: Optional toggle for curious mode
    """
    global current_face, current_offset_x, current_offset_y, current_curious, current_closed

    # Update global variables if parameters are provided
    if face is not None:
        current_face = face
    if curious is not None:
        current_curious = curious
    else:
        curious = current_curious  # Fall back to global curious state
        
    if closed is None:
        closed = current_closed
    else:
        current_closed = closed  # Update global closed state

    logging.info(f"Starting look animation towards {direction} at {speed} speed with face: {current_face}, curious={curious}")

    # Get movement constraints
    min_x_offset, max_x_offset, min_y_offset, max_y_offset = get_constraints(config, device)

    # Determine target offsets based on direction
    if direction == "L":
        target_offset_x = min_x_offset
        target_offset_y = current_offset_y
    elif direction == "R":
        target_offset_x = max_x_offset
        target_offset_y = current_offset_y
    elif direction == "T":
        target_offset_x = current_offset_x
        target_offset_y = min_y_offset
    elif direction == "B":
        target_offset_x = current_offset_x
        target_offset_y = max_y_offset
    elif direction == "TL":
        target_offset_x = min_x_offset
        target_offset_y = min_y_offset
    elif direction == "TR":
        target_offset_x = max_x_offset
        target_offset_y = min_y_offset
    elif direction == "BL":
        target_offset_x = min_x_offset
        target_offset_y = max_y_offset
    elif direction == "BR":
        target_offset_x = max_x_offset
        target_offset_y = max_y_offset
    else:  # Center
        target_offset_x = 0
        target_offset_y = 0

    # Pass the animation command to `draw_eyes`
    draw_eyes(
        device,
        config,
        face=current_face,
        curious=curious,
        closed=current_closed,
        command="look",
        target_offset_x=target_offset_x,
        target_offset_y=target_offset_y,
        speed=speed,
    )
def blink(device, config, eye="both", speed="fast", face=None, curious=None, closed=None):
    """
    Pass blink command and parameters to the draw_eyes function.
    """
    global current_face, current_offset_x, current_offset_y, current_curious, current_closed
    logging.info(f"Starting blinking animation for {eye} eye(s) at {speed} speed with face: {current_face}, curious={curious}")
    
    if closed is None:
        closed = current_closed
    else:
        current_closed = closed  # Update global closed state
        
    draw_eyes(
        device,
        config,
        offset_x=current_offset_x,
        offset_y=current_offset_y,
        face=current_face,
        curious=curious,
        command="blink",
        speed=speed,
        eye=eye,
    )

def eye_close(device, config, eye="both", speed="medium", face=None, curious=None, closed=None):
    """
    Pass close command and parameters to the draw_eyes function.
    """
    global current_face, current_offset_x, current_offset_y, current_curious, current_closed
    logging.info(f"Starting closing animation for {eye} eye(s) at {speed} speed with face: {current_face}, curious={curious}")
    
    if closed is None:
        closed = current_closed
    else:
        current_closed = closed  # Update global closed state
        
    draw_eyes(
        device,
        config,
        offset_x=current_offset_x,
        offset_y=current_offset_y,
        face=current_face,
        curious=curious,
        command="close",
        speed=speed,
        eye=eye,
    )
    
def eye_open(device, config, eye="both", speed="medium", face=None, curious=None, closed=None):
    """
    Pass open command and parameters to the draw_eyes function.
    """
    global current_face, current_offset_x, current_offset_y, current_curious, current_closed
    logging.info(f"Starting opening animation for {eye} eye(s) at {speed} speed with face: {current_face}, curious={curious}")
    
    if closed is None:
        closed = current_closed
    else:
        current_closed = closed  # Update global closed state
    draw_eyes(
        device,
        config,
        offset_x=current_offset_x,
        offset_y=current_offset_y,
        face=current_face,
        curious=curious,
        command="open",
        speed=speed,
        eye=eye,
    )

def main():
    # Load screen and render configurations
    screen_config = load_config("screenconfig.toml", DEFAULT_SCREEN_CONFIG)
    render_config = load_config("eyeconfig.toml", DEFAULT_RENDER_CONFIG)
    # Merge configurations
    config = {**screen_config, **render_config}
    # Initialize the display device
    device = get_device(config)

    # Main loop to test look functionality
    draw_eyes(device, config)
    time.sleep(1)
    draw_eyes(device, config, face="angry")
    time.sleep(1)
    blink(device, config, speed="fast")
    time.sleep(1)

    # Close the eyes
    eye_close(device, config, speed="slow")
    time.sleep(1)
    eye_open(device, config, speed="slow")
    time.sleep(1)

    # Close the left eye
    # eye_close(device, config, speed="fast", eye="left")
    # time.sleep(1)
    # eye_open(device, config, speed="fast", eye="left")
    # time.sleep(1)

    # Close the right eye
    # eye_close(device, config, speed="fast", eye="right")
    # time.sleep(1)
    # eye_open(device, config, speed="fast", eye="right")

    look(device, config, direction="L", speed="fast", curious=True)

    eye_close(device, config, speed="medium")
    time.sleep(1)
    look(device, config, direction="T", speed="fast", face="tired", curious=False)
    eye_open(device, config, speed="medium")
    time.sleep(1)
    
    look(device, config, direction="T", speed="fast", face="tired", curious=False)
    time.sleep(1)
    blink(device, config, speed="fast", eye="left")
    time.sleep(1)
    blink(device, config, speed="fast", eye="right")
    time.sleep(1)
    blink(device, config, speed="medium")

    look(device, config, direction="R", speed="fast", face="tired", curious=True)
    time.sleep(1)
    blink(device, config, speed="medium", eye="left")
    time.sleep(1)
    blink(device, config, speed="fast", eye="right")
    time.sleep(1)
    blink(device, config, speed="slow")

    look(device, config, direction="TL", speed="medium")  # Look left slowly
    blink(device, config, speed="medium", eye="left")
    time.sleep(1)

    look(device, config, direction="TR", speed="medium")  # Look top-right at medium speed
    blink(device, config, speed="medium", eye="right")
    time.sleep(1)

    look(device, config, direction="T", speed="medium")  # Look top-right at medium speed
    time.sleep(1)

    look(device, config, direction="C", speed="fast")
    draw_eyes(device, config, face="happy")
    time.sleep(1)

if __name__ == "__main__":
    main()