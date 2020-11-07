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
import numpy.linalg
import pathlib
import time
import math

COORDS = {
    (1920, 1080): {
        "minimap_center": (918, 209),
        "minimap_radius": 80,
    }
}


logger = logging.getLogger(__name__)

cwd = pathlib.Path.cwd()


numpy.set_printoptions(formatter={'float': "{:.3f}".format})


class IMG():
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

    @functools.cached_property
    def gray(self):
        return cv.cvtColor(self.rgb, cv.COLOR_RGB2GRAY)

    @functools.cached_property
    def smooth(self):
        return cv.fastNlMeansDenoising(self.gray, 30, 7, 11, )

    @functools.cached_property
    def edges(self):
        return cv2.Canny(self.gray, 100, 200)

def get_test_image(p):
    img = PIL.Image.open(p)
    return IMG(image=img)


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
    img = PIL.ImageGrab.grab(r, all_screens=True)
    return IMG(image=img)


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


def angle_from_rot_matrix(M):
    return - math.atan2(M[0, 1], M[0, 0])


class S2():
    last_minimap = None
    _debug_path = None
    _debug_wait_key = None



    def __init__(self, image_save_path=None, debug_mode=None):
        self.image_save_path = image_save_path
        self.debug_mode = debug_mode
        self.map = IMG(image=PIL.Image.open("map.png"))
        self.map.edges = numpy.array(PIL.Image.open("map_edges.bmp"))
        self.pos = 3100, 2600

    def setup_hotkeys(self):
        import hotkey
        hotkey.start()
        self.grabHk = hotkey.HotKey("F7", self.update)
        self.finishHk = hotkey.EventHotKey("F6")

    def run(self):
        # self.setup_hotkeys()
        # self.finishHk.wait()
        while True:
            time.sleep(100)
            self.update()

    def test(self, image_paths):
        for ip in image_paths:
            self._debug_path = f"{ip.parent}/{ip.stem}-{{tag}}{ip.suffix}"
            img = get_test_image(ip)
            info = self.parse_image(img)
            print(ip, info)
            if self._debug_wait_key:
                self._debug_wait_key = False
                cv.waitKey(1000)

    def update(self):
        img = get_image()

        time = time.time()
        datetime = datetime.datetime.now()
        if self.image_save_path:
            p = pathlib.Path(self.image_save_path.format(date=date, time=time))
            img.image.save(p)
            self._debug_path = f"{p.parent}/{p.stem}-{{tag}}{p.suffix}"

        self.handle_image(img)

    def debug_img(self, function):
        if not self.debug_mode:
            return
        name = function.__name__
        if "break" in self.debug_mode:
            breakpoint()
        img = function()
        if "save" in self.debug_mode:
            p = self._debug_path.format(tag=name)
            PIL.Image.fromarray(img).save(p)
        if "show" in self.debug_mode:
            cv.imshow(name, img)
            self._debug_wait_key = True

    def parse_image(self, img):
        done = self.parse_map(img)
        if not done:
            done = self.parse_minimap(img)


    def parse_map(self, img):
        black_map_pixels = img.rgb[0:10, 500:510]
        if (black_map_pixels == 0).all():
            return True # everything with a large black patch is a map to me


    def map_features(self):
        # TODO: Snap to grid and cache
        x, y = self.pos

        slices = (
                slice(y-200, y+200),
                slice(x-200, x+200),
                )

        box_edges = self.map.edges[slices]
        kp, des = self.akaze.detectAndCompute(
            box_edges,
            None,
            )

        return kp, des, slices


    def parse_minimap(self, img):
        coords = COORDS[(img.width, img.height)]
        cx, cy = coords['minimap_center']
        r = coords['minimap_radius']

        minimap = IMG(rgb=img.rgb[cx - r:cx + r, cy - r:cy + r, :])

        a = self.get_minimap_arrow(minimap)
        if a is None:
            return False

        #outer_mask = circle_mask(shape)
        #inner_mask = circle_mask(shape, radius=15)
        #mask = ~(inner_mask & outer_mask)
        # https://docs.opencv.org/master/db/d70/tutorial_akaze_matching.html
        minimap_keypoints, minimap_descriptors = (
                self.akaze.detectAndCompute(
                    minimap.edges,
                    None,  # TODO: Mask
                    )
                )


        map_keypoints, map_descriptors, offset = (
                self.map_features()
            )

        matches = self.dm.knnMatch(minimap_descriptors, map_descriptors, 2)
        good = [m for m, n in matches
                if m.distance < 0.8 * n.distance]

        @self.debug_img
        def akaze_matches():
            return cv.drawMatches(
                minimap.rgb,
                minimap_keypoints,
                self.map.rgb[offset],
                map_keypoints,
                good,
                None,
                flags=cv.DrawMatchesFlags_NOT_DRAW_SINGLE_POINTS,
            )

        if len(good) < 8:
            logger.info(
                "Did not find enough good matches, %d %d",
                len(matches),
                len(good))
            return False

        src_pts = np.float32(
            [minimap_keypoints[m.queryIdx].pt for m in good]).reshape(-1, 1, 2)
        dst_pts = np.float32(
            [map_keypoints[m.trainIdx].pt for m in good]).reshape(-1, 1, 2)

        M = self.get_translation(img, src_pts, dst_pts)
        if M is None:
            logger.info(
                "Did not find Transformation Matrix",
                len(matches),
                len(good))
            return None

        minimap_center = [minimap.width / 2, minimap.height / 2, 1]

        box_center = M @ minimap_center

        scale = box_center[2]
        box_center /= scale
        box_center = box_center[:2]

        pos = box_center + [offset[1].start, offset[0].start]
        pos = numpy.uint32(pos)

        dist = pos - self.pos

        rot = angle_from_rot_matrix(M)

        logger.debug("Translation Matrix: \n%r", M)
        logger.debug("Center In Box: %r", box_center)
        logger.debug("Player Pos: %r", pos)
        logger.debug("Player Moved: %d,%d  = %d", dist, numpy.linalg.norm(dist))
        logger.debug("Scale: %r", scale)
        logger.debug("Angle: %r°", rot * 180 / math.pi)

        @self.debug_img
        def minimap_with_previous_position():
            arrow = [minimap.width / 2, 0, 1]
            arrow = M @ arrow
            arrow /= arrow[2]
            arrow = arrow[:2]

            arrow = int(arrow[0]), int(arrow[1])
            bc = tuple(numpy.uint32(box_center))

            return cv2.line(
                self.map.rgb[offset].copy(),
                bc,
                arrow,
                (0x00, 0xFF, 0xFF),
                4,
            )

    akaze = cv.AKAZE_create()
    dm = cv.DescriptorMatcher_create(cv.DescriptorMatcher_BRUTEFORCE_HAMMING)



    def get_translation(self, img, src_pts, dst_pts):
        M, mask = cv.findHomography(
            src_pts,
            dst_pts,
            cv.RANSAC,
            2,
            None,
            1000,
            0.999)
        return M

    def get_minimap_arrow(self, mm):
        """ Look for the Minimap Arrow.

        Finds contours of white area, approximates a Poly and selects one that
        is in the middle of the map and has 3 corners.
        """
        h, w = mm.height, mm.width
        cy, cx = h // 2, w // 2

        _, v = cv.threshold(mm.gray, 0xDA, 255, cv.THRESH_BINARY)
        contours, hierarchy = cv.findContours(
            v,
            cv.RETR_TREE,
            cv.CHAIN_APPROX_SIMPLE,
        )

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
