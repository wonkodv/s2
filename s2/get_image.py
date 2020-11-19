import logging
import sys

import numpy
import PIL.Image
import PIL.ImageGrab

from s2.config import get_config
from s2.util import IMG

logger = logging.getLogger(__name__)

if sys.platform == "win32":
    from .hwnd import Window


_debug_image_counter = 0


def _get_debug_image(area):
    global _debug_image_counter
    p = get_config("debug", "images")[_debug_image_counter]

    logger.debug(
        "using Debug image %d: %s",
        _debug_image_counter,
        p,
    )
    _debug_image_counter += 1

    i = PIL.Image.open(p)
    if area:
        l, t, r, b = area
        rgb = numpy.array(i)
        rgb = rgb[t:b, l:r]
        return IMG.from_rgb(rgb)
    return IMG.from_image(i)


_last_wnd = None


def get_image(area=None):
    """Screenshot current ForeGroundWin if it matches."""

    debug_images = get_config("debug", "images")
    if debug_images:
        return _get_debug_image(area)

    title = get_config("get_image", "title")
    size = get_config("get_image", "size")

    wnd = Window.get_foreground_window()
    global _last_wnd

    if not wnd:
        if _last_wnd != wnd:
            _last_wnd = wnd
            logger.info("Not real window %r", wnd)
        return None

    if title and wnd.text != title:
        if _last_wnd != wnd:
            _last_wnd = wnd
            logger.info("Title MisMatch %s %r", title, wnd)
        return None

    *r, w, h = wnd.rect

    if size and size != (w, h):
        if _last_wnd != wnd:
            _last_wnd = wnd
            logger.info("Size Mismatch %s, %r", r, wnd)
        return None

    if area:
        x, y = r[:2]
        l, t, r, b = area
        r = l + x, t + y, r + x, t + y

    img = PIL.ImageGrab.grab(r, all_screens=True)
    img = IMG(image=img)
    return img
