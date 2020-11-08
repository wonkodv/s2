import PIL.Image
import PIL.ImageGrab
import PIL.ImageTk
import cv2
import logging
import numpy
import time
import collections

from functools import cache, cached_property
from hwnd import Window

logger = logging.getLogger(__name__)

Update = collections.namedtuple("Update", "x y alpha id")


class IMG:
    """Collection of the various ways a image can be represented."""

    def __init__(self, *, image=None, rgb=None):
        self._image = image
        self._rgb = rgb
        if image is not None:
            self.width = image.width
            self.height = image.height
        elif rgb is not None:
            self.height, self.width = rgb.shape[:2]
        else:
            raise TypeError("Must give either image or rgb or both")

    @classmethod
    @cache
    def from_path(cls, p):
        return cls(image=PIL.Image.open(p))

    @property
    def image(self):
        if self._image is None:
            self._image = PIL.Image.fromarray(self._rgb)
        return self._image

    @property
    def rgb(self):
        if self._rgb is None:
            self._rgb = numpy.asarray(self._image)
        return self._rgb

    @cached_property
    def gray(self):
        return cv2.cvtColor(self.rgb, cv2.COLOR_RGB2GRAY)

    @cached_property
    def smooth(self):
        return cv2.fastNlMeansDenoising(self.gray, 30, 7, 11)

    @cached_property
    def edges(self):
        return cv2.Canny(self.gray, 100, 200)

    @cached_property
    def photoimage(self):
        return PIL.ImageTk.PhotoImage(self.image)


def get_image(title=None, size=None):
    """Screenshot current ForeGroundWin if it matches."""

    l = logger.getChild("get_image")
    t = time.perf_counter()
    wnd = Window.get_foreground_window()

    if not wnd:
        l.info("Not real window %r", wnd)
        return None

    if title and wnd.text != title:
        logger.info("Title MisMatch %s %r", title, wnd)
        return None

    *r, w, h = wnd.rect

    if size and size != (w, h):
        l.info("Size Mismatch %s, %r", r, wnd)
        return None

    img = PIL.ImageGrab.grab(r, all_screens=True)
    img = IMG(image=img)
    t = time.perf_counter() - t
    l.debug("Screen Grab took %.6f seconds, %r", t, wnd)
    return img
