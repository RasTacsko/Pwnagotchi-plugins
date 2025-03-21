import logging
import sys
import toml
import random
import time
import math
import threading
from PIL import Image, ImageDraw
from luma.core.interface.serial import i2c, spi
import luma.oled.device as oled
import luma.lcd.device as lcd
import pantilthat

# Enable debug logging
logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s - %(levelname)s - %(message)s",
)

# Default configuration for the OLED screen
DEFAULT_SCREEN_CONFIG = {
    "screen": {
        "type": "oled",
        "driver": "sh1107",
        "width": 128,
        "height": 128,
        "rotate": 2,
        "interface": "i2c",
        "i2c": {
            "address": "0x3d",
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
              face=None, curious=None, command=None, target_offset_x=None, target_offset_y=None, speed="medium", 
              eye="both", closed=None):
    """
    Draw the eyes on the display with optional face-based eyelids and support for curious mode.
    Automatically adjusts eyelids when the face value changes.

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

    # Check if the face value is changing
    if face is None:
        face = current_face
    elif face != current_face:  # Face has changed
        previous_face = current_face
        current_face = face  # Update global face state

        # Determine target eyelid positions based on the new face
        if face == "happy":
            target_eyelid_heights = {
                "top_inner_left": 0,
                "top_outer_left": 0,
                "bottom_left": config["eye"]["left"]["height"] // 2,
                "top_inner_right": 0,
                "top_outer_right": 0,
                "bottom_right": config["eye"]["right"]["height"] // 2,
            }
        elif face == "angry":
            target_eyelid_heights = {
                "top_inner_left": config["eye"]["left"]["height"] // 2,
                "top_outer_left": 0,
                "bottom_left": 0,
                "top_inner_right": config["eye"]["right"]["height"] // 2,
                "top_outer_right": 0,
                "bottom_right": 0,
            }
        elif face == "tired":
            target_eyelid_heights = {
                "top_inner_left": 0,
                "top_outer_left": config["eye"]["left"]["height"] // 2,
                "bottom_left": 0,
                "top_inner_right": 0,
                "top_outer_right": config["eye"]["right"]["height"] // 2,
                "bottom_right": 0,
            }
        else:  # Default to fully open state
            target_eyelid_heights = {
                "top_inner_left": 0,
                "top_outer_left": 0,
                "bottom_left": 0,
                "top_inner_right": 0,
                "top_outer_right": 0,
                "bottom_right": 0,
            }

        # Adjust eyelids dynamically
        adjustment_speed = 2  # Pixels per frame
        current_eyelid_positions = {
            "top_inner_left": 0,
            "top_outer_left": 0,
            "bottom_left": 0,
            "top_inner_right": 0,
            "top_outer_right": 0,
            "bottom_right": 0,
        }

        while any(
            current_eyelid_positions[key] != target_eyelid_heights[key]
            for key in target_eyelid_heights
        ):
            for key in current_eyelid_positions:
                if current_eyelid_positions[key] < target_eyelid_heights[key]:
                    current_eyelid_positions[key] = min(
                        current_eyelid_positions[key] + adjustment_speed,
                        target_eyelid_heights[key],
                    )
                elif current_eyelid_positions[key] > target_eyelid_heights[key]:
                    current_eyelid_positions[key] = max(
                        current_eyelid_positions[key] - adjustment_speed,
                        target_eyelid_heights[key],
                    )

            # Render the frame
            draw_eyes(
                device,
                config,
                offset_x=current_offset_x,
                offset_y=current_offset_y,
                blink_height_left=blink_height_left,
                blink_height_right=blink_height_right,
                face=face,
                curious=current_curious,
                command=None,  # Prevent recursion
            )
            # time.sleep(1 / config["render"].get("fps", 30))

        return  # Exit after adjustment

    # Default to global curious state if not explicitly provided
    if curious is None:
        curious = current_curious
    else:
        current_curious = curious  # Update global curious state
        
    if closed is None:
        closed = current_closed
    else:
        current_closed = closed  # Update global closed state

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
    
    if blink_height_left is not None or blink_height_right is not None:  # Animation in progress
        eye_height_left = blink_height_left if blink_height_left is not None else left_eye["height"]
        eye_height_right = blink_height_right if blink_height_right is not None else right_eye["height"]
    elif closed == "both":
        eye_height_left = 1
        eye_height_right = 1
    elif closed == "left":
        eye_height_left = 1
        eye_height_right = right_eye["height"]
    elif closed == "right":
        eye_height_left = left_eye["height"]
        eye_height_right = 1
    else:  # Open state
        eye_height_left = left_eye["height"]
        eye_height_right = right_eye["height"]

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

    if command == "look" and target_offset_x is not None and target_offset_y is not None:
        # Define movement speed
        movement_speed = {"fast": 8, "medium": 4, "slow": 2}.get(speed, 4)
        while current_offset_x != target_offset_x or current_offset_y != target_offset_y:
            # Calculate new offsets
            if current_offset_x < target_offset_x:
                current_offset_x = min(current_offset_x + movement_speed, target_offset_x)
            elif current_offset_x > target_offset_x:
                current_offset_x = max(current_offset_x - movement_speed, target_offset_x)

            if current_offset_y < target_offset_y:
                current_offset_y = min(current_offset_y + movement_speed, target_offset_y)
            elif current_offset_y > target_offset_y:
                current_offset_y = max(current_offset_y - movement_speed, target_offset_y)

            # Determine eye heights based on `current_closed`
            if current_closed == "both":
                blink_height_left = 1
                blink_height_right = 1
            elif current_closed == "left":
                blink_height_left = 1
                blink_height_right = config["eye"]["right"]["height"]
            elif current_closed == "right":
                blink_height_left = config["eye"]["left"]["height"]
                blink_height_right = 1
            else:  # Open state
                blink_height_left = config["eye"]["left"]["height"]
                blink_height_right = config["eye"]["right"]["height"]

            # Render the frame
            draw_eyes(
                device,
                config,
                offset_x=current_offset_x,
                offset_y=current_offset_y,
                blink_height_left=blink_height_left,
                blink_height_right=blink_height_right,
                face=current_face,
                curious=curious,
                closed=current_closed,
            )

            # Allow smooth animation
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
                curious=current_curious,
            )

            # Break when the eyes are fully closed
            if (blink_height_left <= 1 and eye in ["both", "left"]) and (
                blink_height_right <= 1 and eye in ["both", "right"]
            ):
                current_closed = "both"  # Update state to closed
                break
            elif blink_height_left <= 1 and eye in ["both", "left"]:
                current_closed = "left"  # Update state to closed
                break
            elif blink_height_right <= 1 and eye in ["both", "right"]:
                current_closed = "right"  # Update state to closed
                break

    # Handle eye opening
    elif command == "open":
        if not current_closed:  # If eyes are already open, skip animation
            logging.warning("Eyes are already open. Skipping animation.")
            return

        # Default blink heights based on current_closed state
        left_eye_height_orig = config["eye"]["left"]["height"]
        right_eye_height_orig = config["eye"]["right"]["height"]

        # Ensure blink heights are initialized to their closed state
        if current_closed == "both":
            blink_height_left = 1
            blink_height_right = 1
        elif current_closed == "left":
            blink_height_left = 1
            blink_height_right = right_eye_height_orig
        elif current_closed == "right":
            blink_height_left = left_eye_height_orig
            blink_height_right = 1
        else:
            # If eyes are already open, no need for animation
            logging.info("Eyes are already open. Skipping opening animation.")
            return

        # Define the speed of animation in pixels per frame
        movement_speed = {"fast": 12, "medium": 8, "slow": 4}.get(speed, 4)

        while True:
            if eye in ["both", "left"]:
                blink_height_left = min(left_eye_height_orig, blink_height_left + movement_speed)
            if eye in ["both", "right"]:
                blink_height_right = min(right_eye_height_orig, blink_height_right + movement_speed)

            # Draw the current frame of the open animation
            draw_eyes(
                device,
                config,
                offset_x=current_offset_x,
                offset_y=current_offset_y,
                blink_height_left=blink_height_left,
                blink_height_right=blink_height_right,
                face=current_face,
                curious=current_curious,
            )

            # Break when the eyes are fully open
            if (blink_height_left >= left_eye_height_orig and eye in ["both", "left"]) and (
                blink_height_right >= right_eye_height_orig and eye in ["both", "right"]
            ):
                current_closed = None  # Update state to open
                break
            elif blink_height_left >= left_eye_height_orig and eye in ["both", "left"]:
                current_closed = "right" if current_closed == "both" else None  # Only right remains closed
                break
            elif blink_height_right >= right_eye_height_orig and eye in ["both", "right"]:
                current_closed = "left" if current_closed == "both" else None  # Only left remains closed
                break

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
    Move the eyes and pan-tilt HAT to a specific position based on the direction.
    Screen animation happens first, followed by smooth servo movement.
    """
    global current_face, current_offset_x, current_offset_y, current_curious, current_closed

    # Update global variables if parameters are provided
    if face is not None:
        current_face = face
    if curious is not None:
        current_curious = curious
    else:
        curious = current_curious

    if closed is None:
        closed = current_closed
    else:
        current_closed = closed

    logging.info(f"Starting look animation towards {direction} at {speed} speed with face: {current_face}, curious={curious}")

    # Get movement constraints
    min_x_offset, max_x_offset, min_y_offset, max_y_offset = get_constraints(config, device)

    # Determine target offsets and pan-tilt angles
    if direction == "L":
        target_offset_x = min_x_offset
        target_offset_y = 0
        target_pan, target_tilt = -33, 0
    elif direction == "R":
        target_offset_x = max_x_offset
        target_offset_y = 0
        target_pan, target_tilt = 33, 0
    elif direction == "T":
        target_offset_x = 0
        target_offset_y = min_y_offset
        target_pan, target_tilt = 0, -33
    elif direction == "B":
        target_offset_x = 0
        target_offset_y = max_y_offset
        target_pan, target_tilt = 0, 33
    elif direction == "TL":
        target_offset_x = min_x_offset
        target_offset_y = min_y_offset
        target_pan, target_tilt = -33, -33
    elif direction == "TR":
        target_offset_x = max_x_offset
        target_offset_y = min_y_offset
        target_pan, target_tilt = 33, -33
    elif direction == "BL":
        target_offset_x = min_x_offset
        target_offset_y = max_y_offset
        target_pan, target_tilt = -33, 33
    elif direction == "BR":
        target_offset_x = max_x_offset
        target_offset_y = max_y_offset
        target_pan, target_tilt = 33, 33
    else:  # Center
        target_offset_x = 0
        target_offset_y = 0
        target_pan, target_tilt = 0, 0

    # Convert speed to duration for smooth movement
    speed_map = {"slow": 0.8, "medium": 0.5, "fast": 0.3}
    duration = speed_map.get(speed, 1)

    # Define the screen animation thread
    def animate_screen():
        draw_eyes(
            device,
            config,
            offset_x=current_offset_x,
            offset_y=current_offset_y,
            face=current_face,
            curious=current_curious,
            command="look",
            target_offset_x=target_offset_x,
            target_offset_y=target_offset_y,
            speed=speed,
        )

    # Define the servo movement thread
    def animate_servos():
        smooth_move(target_pan, target_tilt, duration=duration)

    # Create threads for both tasks
    screen_thread = threading.Thread(target=animate_screen)
    servo_thread = threading.Thread(target=animate_servos)

    # Start both threads
    screen_thread.start()
    servo_thread.start()

    # Wait for both threads to finish
    screen_thread.join()
    servo_thread.join()
    
def smooth_move(target_pan, target_tilt, duration=1.5, step_delay=0.01):
    """
    Smoothly move the pan-tilt HAT to the target position over the given duration,
    using a sinusoidal speed curve for smooth acceleration and deceleration.
    
    :param target_pan: Target pan angle (-90 to 90)
    :param target_tilt: Target tilt angle (-90 to 90)
    :param duration: Total duration for the movement in seconds
    :param step_delay: Delay between each step in seconds
    """
    current_pan = pantilthat.get_pan() or 0
    current_tilt = pantilthat.get_tilt() or 0
    
    steps = int(duration / step_delay)
    
    for i in range(steps):
        # Calculate the progress ratio (0 to 1) with a sinusoidal easing function
        progress = i / steps
        eased_progress = 0.5 * (1 - math.cos(math.pi * progress))  # Sinusoidal easing
        
        # Interpolate the pan and tilt positions
        interpolated_pan = current_pan + (target_pan - current_pan) * eased_progress
        interpolated_tilt = current_tilt + (target_tilt - current_tilt) * eased_progress
        
        # Update the pan-tilt HAT
        pantilthat.pan(round(interpolated_pan))
        pantilthat.tilt(round(interpolated_tilt))
        
        time.sleep(step_delay)

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
    Pass the 'open' command and parameters to the draw_eyes function.
    """
    global current_face, current_offset_x, current_offset_y, current_curious, current_closed

    logging.info(f"Starting opening animation for {eye} eye(s) at {speed} speed with face: {current_face}, curious={curious}")

    # Ensure eyes start from their current closed state
    if current_closed is None:
        logging.warning("Eyes are already open. Skipping animation.")
        return  # Exit if eyes are already open

    # Call the draw_eyes function with the "open" command
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

def wakeup(device, config, eye="both", speed="medium", face=None, curious=None, closed=None):
    """
    Drawing wakeup animation: closed tired, open slow, close slow, open medium, close medium, open fast, default
    """
    global current_face, current_offset_x, current_offset_y, current_curious, current_closed
    draw_eyes(device, config, closed="both")
    draw_eyes(device, config, face="tired")
    time.sleep(2)
    eye_open(device, config, speed="slow")
    eye_close(device, config, speed="slow")
    time.sleep(1)
    eye_open(device, config, speed="medium")
    eye_close(device, config, speed="medium")
    eye_open(device, config, speed="fast")
    draw_eyes(device, config, face="default")

def main():
    # Load screen and render configurations
    screen_config = load_config("screenconfig.toml", DEFAULT_SCREEN_CONFIG)
    render_config = load_config("eyeconfig.toml", DEFAULT_RENDER_CONFIG)

    # Merge configurations
    config = {**screen_config, **render_config}

    # Initialize the display device
    device = get_device(config)

    # Main loop to test wakeup animation
    logging.info(f"Starting main loop to test wakeup animation")
    wakeup(device, config)

    # Main loop to test face change animation
    # logging.info(f"Starting main loop to test face change animation")
    # draw_eyes(device, config)
    # time.sleep(3)    
    # draw_eyes(device, config, face="happy")
    # time.sleep(3)
    # draw_eyes(device, config, face="angry")
    # time.sleep(3)
    # draw_eyes(device, config, face="tired")
    # time.sleep(3)

    # Main loop to test look animation with curious mode on
    logging.info(f"Starting main loop to test look animation with curious mode on")
    look(device, config, direction="C", speed="medium")
    time.sleep(1)
    look(device, config, direction="TL", speed="fast", curious=True)
    time.sleep(1)
    look(device, config, direction="T", speed="fast")
    time.sleep(1)
    look(device, config, direction="TR", speed="fast")
    time.sleep(1)
    look(device, config, direction="L", speed="fast")
    time.sleep(1)
    look(device, config, direction="R", speed="fast")
    time.sleep(1)
    look(device, config, direction="BL", speed="fast")
    time.sleep(1)
    look(device, config, direction="B", speed="fast")
    time.sleep(1)
    look(device, config, direction="BR", speed="fast")
    time.sleep(1)
    look(device, config, direction="C", speed="fast", curious=False)

    # Main loop to test blink animation
    logging.info(f"Starting main loop to test blink animation")
    blink(device, config)
    time.sleep(1)
    blink(device, config, speed="slow", eye="left")
    time.sleep(1)
    blink(device, config, speed="fast", eye="right")

    # Main loop to test close/open animation
    logging.info(f"Starting main loop to test close/open animation")
    eye_close(device, config)
    time.sleep(1)
    eye_open(device, config)
    time.sleep(1)
    eye_close(device, config, speed="slow", eye="left")
    time.sleep(1)
    eye_open(device, config, speed="slow", eye="left")
    time.sleep(1)
    eye_close(device, config, speed="fast", eye="right")
    time.sleep(1)
    eye_open(device, config, speed="fast", eye="right")

if __name__ == "__main__":
    main()