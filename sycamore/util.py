import aggdraw
import math

from functools import lru_cache
from PIL import ImageColor, ImageFont

class Angle():
    RIGHT = 0
    BOTTOM = math.tau / 4
    LEFT = math.tau / 2
    TOP = 3 * math.tau / 4

class Direction():
    CLOCKWISE = 1
    COUNTERCLOCKWISE = -1


def get_rgb(color):
    """Returns 4-tuple representing a color."""
    if isinstance(color, str):
        color = ImageColor.getrgb(color)
    if isinstance(color, tuple) and len(color) == 4:
        return color
    if isinstance(color, tuple) and len(color) == 3:
        return (color[0], color[1], color[2], 255)


@lru_cache(maxsize=128)
def load_font(filename, size=12):
    return ImageFont.truetype(filename, size)

def circular_path(x, y, radius, orbit_duration=30, start_angle=Angle.RIGHT, start_frame=0, direction=Direction.CLOCKWISE):
    """
    Traces a circular path. Circle begins at position (x, y), which is at at angle of start_angle from the origin.
    Circle has radius, and a frame on which animation should begin, and a direction of rotation.
    """
    origin = (x - radius * math.cos(start_angle), y - radius * math.sin(start_angle))
    def compute(i):
        frame = (direction * i - start_frame) % orbit_duration
        angle = start_angle + (math.tau * frame / orbit_duration)
        return {
            "x": origin[0] + radius * math.cos(angle),
            "y": origin[1] + radius * math.sin(angle)
        }
    return compute