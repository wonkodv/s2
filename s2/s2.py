import PIL.ImageGrab
import PIL.Image
import ctypes
import cv2 as cv  # TODO: refactor cv away
import cv2
import datetime
import functools
import logging
import numpy as np  # TODO: refactor np away
import numpy
import numpy.ma
import pathlib
import time
import math

COORDS = {
    (1080, 1920): {
        "minimap_center": (918, 209),
        "minimap_radius": 91,
    }
}

logger = logging.getLogger(__name__)

cwd = pathlib.Path.cwd()


def get_test_image(p):
    img = PIL.Image.open(p)
    rgb = np.asarray(img)
    return rgb, img


def get_image():
    """Screenshot current ForeGroundWin.

        Return PIL Image and numpy RGB Array"""

    import ctypes.wintypes
    w = ctypes.windll.user32.GetForegroundWindow()
    r = ctypes.wintypes.RECT(0, 0, 0, 0)
    p = ctypes.byref(r)
    if not ctypes.windll.user32.GetWindowRect(w, p):
        raise ctypes.WinError()
    r = r.left, r.top, r.right, r.bottom
    i = PIL.ImageGrab.grab(r, all_screens=True)
    n = np.asarray(i)
    return rgb, i


@functools.lru_cache
def circle_mask(shape, center=None, radius=None):
    if not center:
        center = shape[0] // 2, shape[1] // 2
    if not radius:
        radius = min(*center)
    h, w = shape[:2]
    Y, X = np.ogrid[:h, :w]
    dist_from_center = np.sqrt((X - center[0])**2 + (Y - center[1])**2)
    mask = dist_from_center <= radius
    return mask


class S2():
    last_minimap = None

    def __init__(self, image_save_path=None):
        self.image_save_path = image_save_path

    def setup_hotkeys(self):
        import hotkey
        hotkey.start()
        self.grabHk = hotkey.HotKey("F7", self.update)
        self.finishHk = hotkey.EventHotKey("F6")

    def run(self):
        self.setup_hotkeys()
        self.finishHk.wait()

    def test(self, image_paths):
        for ip in image_paths:
            rgb, img = get_test_image(ip)
            info = self.parse_image(rgb)
            print(ip, info)

    def update(self):
        rgb, img = get_image()

        if self.image_save_path:
            p = self.image_save_path.format(
                time=time.time(),
                datetime=datetime.datetime.now(),
            )
            img.save(p)

        self.handle_image(rgb)

    def parse_image(self, rgb):
        info = self.parse_map(rgb)
        if not info:
            info = self.parse_minimap(rgb)
        return info

    def parse_map(self, rgb):
        black_map_pixels = rgb[0:10, 500:510]
        if (black_map_pixels == 0).all():
            return "Looks like a Map"
        else:
            return None

    def parse_minimap(self, rgb):
        coords = COORDS[rgb.shape[:2]]
        cx, cy = coords['minimap_center']
        r = coords['minimap_radius']

        mm = rgb[cx - r:cx + r, cy - r:cy + r, :].copy()
        cm = circle_mask((2 * r, 2 * r))
        mm[~cm] = 0x80, 0x80, 0x80

        a = self.get_minimap_arrow(mm)
        if a is None:
            return False

        for p in a:
            mm[p[1],p[0]] = 0xFF, 0, 0 # TODO: why are the coords inverted?

        PIL.Image.fromarray(mm).save("minimap-crop.png")

        if self.last_minimap is None:
            return "Minimap, but no previous one."
            

        return

    def get_minimap_arrow(self, mm):
        """ Look for the Minimap Arrow.

        Finds contours of white area, approximates a Poly and selects one that
        is in the middle of the map and has 3 corners.
        """
        h, w = mm.shape[:2]
        cy, cx = h//2, w//2

        hsv = cv.cvtColor(mm, cv.COLOR_RGB2HSV)
        v = hsv[:,:,2]
        _, v = cv.threshold(v, 0xDA, 255, cv.THRESH_BINARY)
        contours, hierarchy = cv.findContours(v, cv.RETR_TREE, cv.CHAIN_APPROX_SIMPLE)

        for c in contours:
            poly = cv2.approxPolyDP(c, 4, True)
            if len(poly) == 3:
                y, x = poly[0][0]
                if h * 0.4 < y < h * 0.6 and w * 0.4 < x < w * 0.6:
                    poly = poly[:,0,:]
                    logger.debug("Found Arrow in Minimap %r", poly)
                    return poly
        else:
            return None

