import aggdraw
import copy
import cv2
import math
import numpy
import os

from collections import namedtuple
from PIL import Image as PILImage, ImageColor, ImageDraw

from .util import *

Keyframe = namedtuple("Keyframe", ["start", "end", "compute"])

class StorySequence():
    def __init__(self, width=1920, height=1080):
        """Creates a sequence of stories."""
        self.width = width
        self.height = height
        self.stories = []

    def add_story(self, story):
        self.stories.append(story)

    def output_video(self, filename, fps=30, log=True):
        if os.path.exists(filename):
            os.remove(filename)
        video = cv2.VideoWriter(filename, -1, fps, (self.width, self.height))
        for story in self.stories:
            if isinstance(story, Story):
                for i in range(story.frames):
                    if log:
                        print(f"Writing story {story.name}, frame {i} of {story.frames - 1}...")
                    frame = story.get_frame(i)
                    video.write(cv2.cvtColor(numpy.array(frame), cv2.COLOR_RGB2BGR))
            elif isinstance(story, Video):
                for i, frame in enumerate(story.frames):
                    if log:
                        print(f"Writing story {story.name}, frame {i} of {story.frames - 1}...")
                    video.write(frame)
        video.release()

        
class Story():

    def __init__(self, name="Story", width=1920, height=1080, frames=1, background="white"):
        """Create a new story."""
        self.name = name
        self.width = width
        self.height = height
        self.background = get_rgb(background)
        self.frames = frames
        self.objects = []
    
    def get_frame(self, i):
        """Generate image for a single frame."""
        img = PILImage.new("RGBA", (self.width, self.height), color=self.background)
        for obj in sorted(self.objects, key=lambda obj: obj.layer):
            if obj.present_for_frame(i):
                props = obj.get_props_for_frame(i)
                img = obj.render(img, props, i)
        return img
    
    def output_frame(self, i, filename):
        frame = self.get_frame(i)
        frame.save(filename)

    def output_frames(self, base_filename, start=0):
        """Generate images for multiple frames."""
        digits = 1 + math.floor(math.log10(max(1, start + self.frames - 1)))
        for i in range(self.frames):
            self.output_frame(i, f"{base_filename}_{str(start + i).zfill(digits)}.png")

    def output_video(self, filename, fps=30, log=True):
        if os.path.exists(filename):
            os.remove(filename)
        video = cv2.VideoWriter(filename, -1, fps, (self.width, self.height))
        for i in range(self.frames):
            if log:
                print(f"Writing story {self.name}, frame {i} of {self.frames - 1}...")
            frame = self.get_frame(i)
            video.write(cv2.cvtColor(numpy.array(frame), cv2.COLOR_RGB2BGR))
        video.release()

    def add_object(self, obj):
        self.objects.append(obj)


class Video():
    def __init__(self, filename, name=None):
        self.name = name or filename
        self.frames = []
        vidcap = cv2.VideoCapture(filename)
        while True:
            success, image = vidcap.read()
            if success:
                self.frames.append(image)
            else:
                break


class Object():

    def __init__(self, start=None, end=None, layer=1, props=None):
        self.start = start or 0
        self.end = end
        self.layer = layer
        self.props = props or dict()
        self.keyframes = [
            Keyframe(start=0, end=None, compute=lambda _: self.props)
        ]

    
    def present_for_frame(self, frame):
        """Determines if an object should be shown for a given frame."""
        if frame < (self.start if self.start is not None else 0):
            return False
        if self.end is None:
            return True
        return frame < self.end


    def render(self, img, props, frame):
        return img

    
    def hold_until(self, frame):
        last = self.keyframes[-1]
        del self.keyframes[-1]
        self.keyframes.append(Keyframe(start=last.start, end=frame, compute=last.compute))
        self.keyframes.append(Keyframe(start=frame, end=None, compute=last.compute))

    
    def add_keyframe(self, frame, props, interpolate=True):
        last = self.keyframes[-1]
        del self.keyframes[-1]
        if frame < last.start:
            raise Exception("Adding keyframe before the last start point.")

        # Get final position of previous keyframe
        last_props = last.compute(frame - 1)

        # No interpolation
        if interpolate == False:
            self.keyframes.append(Keyframe(start=last.start, end=frame, compute=last.compute))

            new_props = copy.copy(last_props)
            new_props.update(props)

        # If a specific interpolation function is defined
        elif callable(props):
            def compute(i):
                result = props(i)
                for prop in last_props:
                    if prop not in result:
                        result.setdefault(prop, last_props[prop])
                return result
            self.keyframes.append(Keyframe(start=last.start, end=frame, compute=compute))

            # Get new properties at end of keyframe
            new_props = copy.copy(last_props)
            new_props.update(compute(frame))

        # Interpolation
        else:
            color_props = ["color", "fill", "background", "outline"]
            for prop in color_props:
                if props.get(prop):
                    props[prop] = get_rgb(props[prop])

            # Calculate new props
            new_props = copy.copy(last_props)
            new_props.update(props)

            def compute(i):
                progress = (i - last.start) / (frame - last.start)
                interpolated_props = {}
                for prop in last_props:
                    if isinstance(last_props[prop], int) or isinstance(last_props[prop], float):
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


class Group(Object):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.children = []

    
    def add_child(self, child):
        self.children.append(child)


    def render(self, img, props, frame):
        for child in self.children:
            if child.present_for_frame(frame):
                child_props = child.get_props_for_frame(frame)
                img = child.render(img, child_props, frame, offset=(props["x"], props["y"]))
        return img


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
            self.props[color] = get_rgb(self.props[color])

    def render(self, img, props, frame, offset=(0, 0)):
        x = round(props["x"] + offset[0])
        y = round(props["y"] + offset[1])
        width = round(props["width"])
        height = round(props["height"])
        outline_width = round(props["outline_width"])
        draw = aggdraw.Draw(img)
        pen = aggdraw.Pen(props["outline"], outline_width)
        color = props["fill"]
        brush = aggdraw.Brush((color[0], color[1], color[2]), color[3])
        draw.rectangle((x, y, x + width, y + height), pen, brush)
        draw.flush()
        return img


class Text(Object):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.props.setdefault("x", 0)
        self.props.setdefault("y", 0)
        self.props.setdefault("text", "Text")
        self.props.setdefault("fill", "black")
        self.props.setdefault("font", None)
        self.props.setdefault("size", 12)
        for color in ["fill"]:
            self.props[color] = get_rgb(self.props[color])

    def render(self, img, props, frame, offset=(0, 0)):
        txt = PILImage.new("RGBA", img.size, (255, 255, 255, 0))
        x = round(props["x"] + offset[0])
        y = round(props["y"] + offset[1])
        draw = ImageDraw.Draw(txt)
        font = load_font(props["font"], props["size"])
        draw.text((x, y), props["text"], font=font, fill=props["fill"])
        return PILImage.alpha_composite(img, txt)

    
    def size(self, frame=0):
        props = self.get_props_for_frame(frame)
        txt = PILImage.new("RGBA", (1920, 1080), (255, 255, 255, 0))
        draw = ImageDraw.Draw(txt)
        font = load_font(props["font"], props["size"])
        return draw.textsize(text=props["text"], font=font)

    def center(self, width, height, frame=0):
        text_width, text_height = self.size(frame=frame)
        self.add_keyframe(frame, {
            "x": (width - text_width) / 2,
            "y": (height - text_height) / 2
        })
        

class Arc(Object):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.props.setdefault("x0", 0)
        self.props.setdefault("y0", 0)
        self.props.setdefault("x1", 100)
        self.props.setdefault("y1", 100)
        self.props.setdefault("start_angle", Angle.TOP)
        self.props.setdefault("end_angle", Angle.RIGHT)
        self.props.setdefault("fill", "black")
        self.props.setdefault("width", 5)
        for color in ["fill"]:
            self.props[color] = get_rgb(self.props[color])

    def render(self, img, props, frame, offset=(0, 0)):
        draw = aggdraw.Draw(img)
        x0 = round(props["x0"] + offset[0])
        y0 = round(props["y0"] + offset[1])
        x1 = round(props["x1"] + offset[0])
        y1 = round(props["y1"] + offset[1])
        start_angle = props["start_angle"] * (180 / math.pi)
        end_angle = props["end_angle"] * (180 / math.pi)
        pen = aggdraw.Pen(props["fill"], props["width"])
        draw.arc(
            (x0, y0, x1, y1), start_angle, end_angle, pen
        )
        draw.flush()
        return img


class Ellipse(Object):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.props.setdefault("x0", 0)
        self.props.setdefault("y0", 0)
        self.props.setdefault("x1", 100)
        self.props.setdefault("y1", 100)
        self.props.setdefault("fill", "white")
        self.props.setdefault("outline", "black")
        self.props.setdefault("width", 5)
        for color in ["fill", "outline"]:
            self.props[color] = get_rgb(self.props[color])

    def render(self, img, props, frame, offset=(0, 0)):
        x0 = round(props["x0"] + offset[0])
        y0 = round(props["y0"] + offset[1])
        x1 = round(props["x1"] + offset[0])
        y1 = round(props["y1"] + offset[1])
        draw = aggdraw.Draw(img)
        pen = aggdraw.Pen(props["outline"], props["width"])
        color = props["fill"]
        brush = aggdraw.Brush((color[0], color[1], color[2]), color[3])
        draw.ellipse((x0, y0, x1, y1), pen, brush)
        draw.flush()
        return img

class Image(Object):

    def __init__(self, image, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.image = image
        width, height = image.size
        self.props.setdefault("x", 0)
        self.props.setdefault("y", 0)
        self.props.setdefault("width", width)
        self.props.setdefault("height", height)
        self.props.setdefault("opacity", 255)

    def render(self, img, props, frame, offset=(0, 0)):
        imageLayer = PILImage.new("RGBA", img.size, (255, 255, 255, 0))
        x = round(props["x"] + offset[0])
        y = round(props["y"] + offset[1])
        width = round(props["width"])
        height = round(props["height"])
        if self.image.size != (width, height):
            image = self.image.resize((width, height))
        else:
            image = self.image
        copy = image.copy()
        copy.putalpha(round(props["opacity"]))
        try:
            imageLayer.paste(copy, (x, y), image)
        except ValueError:
            imageLayer.paste(copy, (x, y))
        return PILImage.alpha_composite(img, imageLayer)


class Line(Object):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.props.setdefault("x0", 0)
        self.props.setdefault("y0", 0)
        self.props.setdefault("x1", 100)
        self.props.setdefault("y1", 100)
        self.props.setdefault("color", "black")
        self.props.setdefault("width", 5)
        for color in ["color"]:
            self.props[color] = get_rgb(self.props[color])

    def render(self, img, props, frame, offset=(0, 0)):
        x0 = round(props["x0"] + offset[0])
        y0 = round(props["y0"] + offset[1])
        x1 = round(props["x1"] + offset[0])
        y1 = round(props["y1"] + offset[1])
        draw = aggdraw.Draw(img)
        pen = aggdraw.Pen(props["color"], props["width"])
        draw.line((x0, y0, x1, y1), pen)
        draw.flush()
        return img


class Polygon(Object):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.props.setdefault("coords", [0, 0, 100, 100, 0, 100])
        self.props.setdefault("color", "black")
        self.props.setdefault("fill", "white")
        self.props.setdefault("width", 5)
        for color in ["color", "fill"]:
            self.props[color] = get_rgb(self.props[color])

    def render(self, img, props, frame, offset=(0, 0)):
        coords = [round(coord) for coord in props["coords"]]
        draw = aggdraw.Draw(img)
        pen = aggdraw.Pen(props["color"], props["width"])
        color = props["fill"]
        brush = aggdraw.Brush((color[0], color[1], color[2]), color[3])
        draw.polygon(coords, pen, brush)
        draw.flush()
        return img


class Path(Object):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        default = aggdraw.Path()
        default.moveto(100, 100)
        default.curveto(200, 133, 200, 167, 100, 200)
        self.props.setdefault("path", default)
        self.props.setdefault("color", "black")
        self.props.setdefault("width", 5)
        for color in ["color"]:
            self.props[color] = get_rgb(self.props[color])

    def render(self, img, props, frame, offset=(0, 0)):
        path = props["path"]
        draw = aggdraw.Draw(img)
        pen = aggdraw.Pen(props["color"], props["width"])
        draw.path(path, pen)
        draw.flush()
        return img