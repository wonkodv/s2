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
        "minimap_radius": 80,
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


def dist(p1, p2):
    return math.hypot(p1[0] - p2[0], p1[1] - p2[1])


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
        #self.setup_hotkeys()
        #self.finishHk.wait()
        while 1:
            time.sleep(10)
            self.update

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

        mm_rgb = rgb[cx - r:cx + r, cy - r:cy + r, :]

        mm_gray = cv.cvtColor(mm_rgb, cv.COLOR_RGB2GRAY)

        a = self.get_minimap_arrow(mm_gray)
        if a is None:
            return False

        curr_gray, curr_rgb = mm_gray, mm_rgb

        outer_mask = circle_mask(curr_gray.shape[:2])
        inner_mask = circle_mask(curr_gray.shape[:2], radius=15)
        mask = numpy.zeros(curr_gray.shape[:2])
        mask[~inner_mask] = 1

        #curr_gray[~cm] = 0x81

        curr_gray = cv.fastNlMeansDenoising(curr_gray, 30, 7, 11, )
        #curr_gray = cv2.blur(curr_gray, (3, 3))

        curr_edges = cv2.Canny(curr_gray, 100, 200)

        #curr_edges[cm] = 0

        #sharpen_kernel = np.array([[-1,-1,-1,],[-1,9,-1,],[-1,-1,-1,]])
        #curr_gray = cv2.filter2D(curr_gray, -1, sharpen_kernel)

        #curr_gray = curr_gray // 32
        #curr_gray = curr_gray * 32

        #cv2.imshow("Canny",  curr_edges)

        #kp = cv.FastFeatureDetector_create().detect(curr_edges,None)
        #edges_points = cv.drawKeypoints(edges, kp, None, (0,0,0xFF), cv.DRAW_MATCHES_FLAGS_DRAW_RICH_KEYPOINTS)
        #cv2.imshow("Fast Features in Canny",  edges_points)

        orb = cv.ORB_create()
        curr_kp = orb.detect(curr_edges)
        curr_kp = [p for p in curr_kp if 15 < dist(p.pt, (r, r)) < r - 5]
        edges_points = cv.drawKeypoints( curr_edges, curr_kp, curr_rgb, (0, 0, 0xFF))
        curr_kp, curr_des = orb.compute(curr_edges, curr_kp)

        #curr_rgb_edges = numpy.zeros_like(curr_rgb)
        #curr_rgb_edges[curr_edges == 0] = 0xFF, 0xFF, 0xFF
        #cv2.imshow("curr_rgb_edges", curr_rgb_edges)
        #cv2.waitKey()

        last = self.last_minimap
        self.last_minimap = curr_rgb, curr_gray, curr_edges, curr_kp, curr_des

        if last is None:
            logger.info("No previous minimap to compare to")
            return False

        last_rgb, last_gray, last_edges, last_kp, last_des = last

        bf = cv.BFMatcher(cv.NORM_HAMMING, crossCheck=True)


        matches = bf.match(last_des, curr_des)
        good = [ m for m in matches if m.distance < 50]

        debug = cv.drawMatches(
            last_rgb,
            last_kp,
            curr_rgb,
            curr_kp,
            good,
            None,
            flags=cv.DrawMatchesFlags_NOT_DRAW_SINGLE_POINTS)

        cv.imshow("minimap translation", debug)

        if len(good) < 8:
            logger.info("Did not find enough good matches, %d %d", len(matches), len(good))
            return False

        src_pts = np.float32([ last_kp[m.queryIdx].pt for m in good ]).reshape(-1,1,2)
        dst_pts = np.float32([ curr_kp[m.trainIdx].pt for m in good ]).reshape(-1,1,2)

        M, mask = cv.findHomography(src_pts, dst_pts, cv.RANSAC,5.0)
        if M is None:
            logger.info("Did not find Transformation Matrix", len(matches), len(good))

        matchesMask = mask.ravel().tolist()
        h,w,d = curr_rgb.shape
        pts = np.float32([ [0,0],[0,h-1],[w-1,h-1],[w-1,0] ]).reshape(-1,1,2)
        dst = cv.perspectiveTransform(pts,M)

        theta = - math.atan2(M[0,1], M[0,0]) * 180 / math.pi

        logger.debug("Translation Matrix: %r", M)
        logger.debug("Translation Points: %r", dst)
        logger.debug("Translation Angle: %r", theta)
        return False

    def get_minimap_arrow(self, mm_gray):
        """ Look for the Minimap Arrow.

        Finds contours of white area, approximates a Poly and selects one that
        is in the middle of the map and has 3 corners.
        """
        h, w = mm_gray.shape[:2]
        cy, cx = h // 2, w // 2

        _, v = cv.threshold(mm_gray, 0xDA, 255, cv.THRESH_BINARY)
        contours, hierarchy = cv.findContours(
            v, cv.RETR_TREE, cv.CHAIN_APPROX_SIMPLE)

        for c in contours:
            poly = cv2.approxPolyDP(c, 4, True)
            if len(poly) == 3:
                y, x = poly[0][0]
                if h * 0.4 < y < h * 0.6 and w * 0.4 < x < w * 0.6:
                    poly = poly[:, 0, :]
                    logger.debug("Found Arrow in Minimap %r", poly)
                    return poly
        else:
            return None
