import copy
import cv2
import math
import numpy
import os

from collections import namedtuple
from PIL import Image, ImageColor, ImageDraw

Keyframe = namedtuple("Keyframe", ["start", "end", "compute"])

class Story():

    def __init__(self, width=1920, height=1080, frames=1, background="white"):
        """Create a new story."""
        self.width = width
        self.height = height
        self.background = ImageColor.getrgb(background) if isinstance(background, str) else background
        self.frames = frames
        self.objects = []
    
    def get_frame(self, i):
        """Generate image for a single frame."""
        img = Image.new("RGB", (self.width, self.height), color=self.background)
        draw = ImageDraw.Draw(img, "RGBA")
        for obj in self.objects:
            if obj.present_for_frame(i):
                obj.render(draw, i)
        return img
    
    def output_frame(self, i, filename):
        frame = self.get_frame(i)
        frame.save(filename)

    def output_frames(self, base_filename, start=0):
        """Generate images for multiple frames."""
        digits = 1 + math.floor(math.log10(max(1, start + self.frames - 1)))
        for i in range(self.frames):
            self.output_frame(i, f"{base_filename}_{str(start + i).zfill(digits)}.png")

    def output_video(self, filename, fps=30):
        if os.path.exists(filename):
            os.remove(filename)
        video = cv2.VideoWriter(filename, -1, fps, (self.width, self.height))
        for i in range(self.frames):
            frame = self.get_frame(i)
            video.write(cv2.cvtColor(numpy.array(frame), cv2.COLOR_RGB2BGR))
        video.release()

    def add_object(self, obj):
        self.objects.append(obj)


class Object():


    def __init__(self, start=None, end=None, layer=1, props=None):
        self.start = start or 0
        self.end = end
        self.layer = layer
        self.props = props or dict()
        self.keyframes = [
            Keyframe(start=0, end=None, compute=lambda _: props)
        ]


    def present_for_frame(self, frame):
        """Determines if an object should be shown for a given frame."""
        if frame < (self.start if self.start is not None else 0):
            return False
        if self.end is None:
            return True
        return frame < self.end


    def render(self, draw, frame):
        return

    
    def add_keyframe(self, frame, props, interpolate=True):
        last = self.keyframes[-1]
        del self.keyframes[-1]
        if frame < last.start:
            raise Exception("Adding keyframe before the last start point.")

        color_props = ["fill", "background", "outline"]
        for prop in color_props:
            if isinstance(props.get(prop), str):
                props[prop] = ImageColor.getrgb(props[prop])
            if props.get(prop) and len(props.get(prop)) == 3:
                props[prop] = (props[prop][0], props[prop][1], props[prop][2], 255)

        # Calculate new props
        last_props = last.compute(frame - 1)
        new_props = copy.copy(last_props)
        new_props.update(props)

        # No interpolation
        if interpolate == False:
            self.keyframes.append(Keyframe(start=last.start, end=frame, compute=last.compute))

        # Interpolation
        else:
            def compute(i):
                progress = (i - last.start) / (frame - last.start)
                interpolated_props = {}
                for prop in last_props:
                    if isinstance(last_props[prop], int):
                        interpolated_props[prop] = int(last_props[prop] + progress * (new_props[prop] - last_props[prop]))
                    elif isinstance(last_props[prop], float):
                        interpolated_props[prop] = last_props[prop] + progress * (new_props[prop] - last_props[prop])
                    elif isinstance(last_props[prop], tuple) and len(last_props[prop]) == 4:
                        interpolated_props[prop] = (
                             int(last_props[prop][0] + progress * (new_props[prop][0] - last_props[prop][0])),
                             int(last_props[prop][1] + progress * (new_props[prop][1] - last_props[prop][1])),
                             int(last_props[prop][2] + progress * (new_props[prop][2] - last_props[prop][2])),
                             int(last_props[prop][3] + progress * (new_props[prop][3] - last_props[prop][3]))
                        )
                    else:
                        interpolated_props[prop] = last_props[prop]
                return interpolated_props
            self.keyframes.append(Keyframe(start=last.start, end=frame, compute=compute))
        self.keyframes.append(Keyframe(start=frame, end=None, compute=lambda _: new_props))

    
    def get_props_for_frame(self, frame):
        for keyframe in self.keyframes:
            if keyframe.start <= frame and (keyframe.end is None or frame < keyframe.end):
                return keyframe.compute(frame)
                break


class Rectangle(Object):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.props.setdefault("x", 0)
        self.props.setdefault("y", 0)
        self.props.setdefault("width", 100)
        self.props.setdefault("height", 100)
        self.props.setdefault("fill", "white")
        self.props.setdefault("outline", "black")
        self.props.setdefault("outline_width", 5)
        for color in ["fill", "outline"]:
            if isinstance(self.props[color], str):
                self.props[color] = ImageColor.getrgb(self.props[color])

    def render(self, draw, frame):
        props = self.get_props_for_frame(frame)
        draw.rectangle(
            [(props["x"], props["y"]), (props["x"] + props["width"], props["y"] + props["height"])],
            fill=props["fill"], outline=props["outline"], width=props["outline_width"]
        )


class Text(Object):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.props.setdefault("x", 0)
        self.props.setdefault("y", 0)
        self.props.setdefault("text", "Text")
        self.props.setdefault("fill", "TODO: need to figure out coloring")