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


class S2():
    last_minimap = None
    _debug_path = None
    _debug_wait_key = None

    def __init__(self, image_save_path=None, debug_mode=None):
        self.image_save_path = image_save_path
        self.debug_mode = debug_mode
        self.map = IMG(image=PIL.Image.open("map.png"))
        self.map.edges = numpy.array(PIL.Image.open("map_edges.bmp"))

        self.akaze = cv.AKAZE_create()
        self.dm = cv.DescriptorMatcher_create(
            cv.DescriptorMatcher_BRUTEFORCE_HAMMING)

        self.pos = 3100, 2600
        self.heading = 0
        self.updates_since_last_fix = 0

        self._map_feature_cache = {}

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
            # print(ip, info)
            if self._debug_wait_key:
                self._debug_wait_key = False
                if 'wait' in self.debug_mode:
                    wait = True
                    # catch Keyboard Interrupt every 100ms
                    while wait:
                        wait = cv.waitKey(100) < 0
                else:
                    cv.waitKey(1)

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
        @self.debug_img
        def current_screen_grab():
            return img.rgb
        done = self.parse_map(img)
        if not done:
            done = self.parse_minimap(img)

        if done:
            self.updates_since_last_fix = 0
        else:
            self.updates_since_last_fix += 0

    def parse_map(self, img):
        black_map_pixels = img.rgb[0:10, 500:510]
        if (black_map_pixels == 0).all():
            return True  # everything with a large black patch is a map to me

    def map_features(self):
        x, y = self.pos

        # todo: add based on speed and heading ?
        groups = 64 # cach features for 64 by 64 pixel blocks.
        box_size = 512

        x |= groups-1
        y |= groups-1

        slices = (
            slice(y - box_size//2 - groups//2, y + box_size//2 - groups//2),
            slice(x - box_size//2 - groups//2, x + box_size//2 - groups//2),
        )

        key = x, y
        features = self._map_feature_cache.get(key)
        if features is None:
            features = self.akaze.detectAndCompute(
                self.map.edges[slices], None)
            self._map_feature_cache[key] = features

        return features, slices

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

        (map_keypoints, map_descriptors), offset_slices = (
            self.map_features()
        )

        offset = numpy.array([offset_slices[1].start, offset_slices[0].start])

        matches = self.dm.knnMatch(minimap_descriptors, map_descriptors, 2)
        good = [m for m, n in matches
                if m.distance < 0.8 * n.distance]

        # TODO: calculate center of good, then filter map_features by distance
        # and match again

        if len(good) < 6:
            @self.debug_img
            def minimap_with_match():
                box = self.map.rgb[offset_slices].copy()
                op = tuple(self.pos - offset)
                cv2.circle(box, op, 5, (0x00, 0x00, 0xFF), 1,)
                return cv2.drawMatches(
                    minimap.rgb,
                    minimap_keypoints,
                    box,
                    map_keypoints,
                    good,
                    None,
                    flags=cv.DrawMatchesFlags_NOT_DRAW_SINGLE_POINTS,
                )
            return True
            logger.debug(
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
            )
            return None

        minimap_center = [minimap.width / 2, minimap.height / 2, 1]

        position_in_box = M @ minimap_center

        scale = position_in_box[2]
        position_in_box /= scale
        position_in_box = position_in_box[:2]

        pos = position_in_box + offset
        pos = numpy.int32(pos)

        delta = pos - self.pos
        dist = numpy.linalg.norm(delta)

        heading = -math.atan2(M[0, 1], M[0, 0]) * 180 / math.pi % 360

        old_pos = self.pos


        @self.debug_img
        def minimap_with_match():

            arrow = [minimap.width / 2, 0, 1]
            arrow = M @ arrow
            arrow /= arrow[2]
            arrow = arrow[:2]

            arrow.clip(0, 512)

            arrow = int(arrow[0]), int(arrow[1])
            bc = tuple(numpy.uint32(position_in_box))
            op = tuple(old_pos - offset)

            box = self.map.rgb[offset_slices].copy()

            cv2.arrowedLine(box, bc, arrow, (0x00, 0xFF, 0xFF), 1,)

            cv2.circle(box, op, 5, (0x00, 0x00, 0xFF), 1,)
            return cv2.drawMatches(
                minimap.rgb,
                minimap_keypoints,
                box,
                map_keypoints,
                good,
                None,
                flags=cv.DrawMatchesFlags_NOT_DRAW_SINGLE_POINTS,
            )

        # calculate expected position based on speed, heading and last fix

        if dist > 300:
            logger.info("Discarded %s %d°  moved %f", pos, heading, dist)
            return False

        self.pos = pos
        self.heading = heading

        logger.info("Position update %s %d°  moved %f", pos, heading, dist)
        return True

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
