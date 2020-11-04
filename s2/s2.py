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
    (1920, 1080): {
        "minimap_center": (918, 209),
        "minimap_radius": 80,
    }
}

logger = logging.getLogger(__name__)

cwd = pathlib.Path.cwd()


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


def dist(p1, p2):
    return math.hypot(p1[0] - p2[0], p1[1] - p2[1])


def angle_from_rot_matrix(M):
    return - math.atan2(M[0, 1], M[0, 0]) * 180 / math.pi

class S2():
    last_minimap = None
    _debug_path = None
    _debug_wait_key = None

    def __init__(self, image_save_path=None, debug_mode=None):
        self.image_save_path = image_save_path
        self.debug_mode = debug_mode

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
                cv.waitKey()

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
        info = self.parse_map(img)
        if not info:
            info = self.parse_minimap(img)
        return info

    def parse_map(self, img):
        black_map_pixels = img.rgb[0:10, 500:510]
        if (black_map_pixels == 0).all():
            return "Looks like a Map"
        else:
            return None

    def parse_minimap(self, img):
        coords = COORDS[(img.width, img.height)]
        cx, cy = coords['minimap_center']
        r = coords['minimap_radius']

        mm = IMG(rgb=img.rgb[cx - r:cx + r, cy - r:cy + r, :])

        a = self.get_minimap_arrow(mm)
        if a is None:
            return False

        points = self.parse_minimap_mapper(mm)
        if not points:
            return False
            T = self.get_translation(*points)

    mapper = cv2.reg_MapperGradEuclid()
    def parse_minimap_mapper(self, curr):
        assert curr.width == curr.height
        shape = curr.height, curr.width
        r = curr.width // 2
        curr_gray = curr.gray
        outer_mask = circle_mask(shape)
        inner_mask = circle_mask(shape, radius=15)
        mask = ~(inner_mask & outer_mask)

        curr_gray = cv.fastNlMeansDenoising(curr_gray, 30, 7, 11, )
        curr_edges = cv2.Canny(curr_gray, 100, 200)


        last = self.last_minimap
        self.last_minimap = curr, curr_edges

        if last is None:
            logger.info("No previous minimap to compare to")
            return False

        last_img, last_edges = last

        @self.debug_img
        def edges():
            return np.concatenate((last_edges, curr_edges), axis=1)

        m = self.mapper.calculate(last_edges, curr_edges)
        m = cv.reg.MapTypeCaster_toAffine(m)

        shift = m.getShift()
        M = m.getLinTr()
        theta = angle_from_rot_matrix(M)

        logger.debug("shift: %r angle : %f  M: %r", shift, theta, M)


    orb = cv.ORB_create(scaleFactor=1.3)
    bf = cv.BFMatcher(cv.NORM_HAMMING, crossCheck=True)
    def parse_minimap_orb(self, curr):
        assert curr.width == curr.height
        shape = curr.height, curr.width
        r = curr.width // 2
        curr_gray = curr.gray
        outer_mask = circle_mask(shape)
        inner_mask = circle_mask(shape, radius=15)
        mask = ~(inner_mask & outer_mask)

        curr_gray = cv.fastNlMeansDenoising(curr_gray, 30, 7, 11, )
        curr_edges = cv2.Canny(curr_gray, 100, 200)

        curr_kp = self.orb.detect(curr_edges, mask)
        #curr_kp = [p for p in curr_kp if 15 < dist(p.pt, (r, r)) < r - 5]

        @self.debug_img
        def orb_key_points_in_canny_edges():
            return cv.drawKeypoints(
                curr_edges,
                curr_kp,
                None,
                (0, 0, 0xFF))

        curr_kp, curr_des = self.orb.compute(curr_edges, curr_kp)

        last = self.last_minimap
        self.last_minimap = curr, curr_edges, curr_kp, curr_des

        if last is None:
            logger.info("No previous minimap to compare to")
            return False

        last_img, last_edges, last_kp, last_des = last

        matches = self.bf.match(last_des, curr_des)
        good = [m for m in matches if m.distance < 50]

        @self.debug_img
        def orb_matches():
            return cv.drawMatches(
                last_img.rgb,
                last_kp,
                curr.rgb,
                curr_kp,
                good,
                None,
                flags=cv.DrawMatchesFlags_NOT_DRAW_SINGLE_POINTS)

        if len(good) < 8:
            logger.info(
                "Did not find enough good matches, %d %d",
                len(matches),
                len(good))
            return False

        src_pts = np.float32(
            [last_kp[m.queryIdx].pt for m in good]).reshape(-1, 1, 2)
        dst_pts = np.float32(
            [curr_kp[m.trainIdx].pt for m in good]).reshape(-1, 1, 2)

        return src_pts, dst_pts

    if False:
        bd = cv.line_descriptor_BinaryDescriptor_createBinaryDescriptor()
        bdm = cv.line_descriptor_BinaryDescriptorMatcher()
        def parse_minimap_lines(self, curr):
            assert curr.width == curr.height
            shape = curr.height, curr.width
            r = curr.width // 2
            curr_gray = curr.gray
            outer_mask = circle_mask(shape)
            inner_mask = circle_mask(shape, radius=15)
            mask = ~(inner_mask & outer_mask)

            curr_gray = cv.fastNlMeansDenoising(curr_gray, 30, 7, 11, )
            curr_edges = cv2.Canny(curr_gray, 100, 200)

            curr_kp = self.bd.detect(curr_edges) # TODO: Mask
            #curr_kp = [p for p in curr_kp if 15 < dist(p.pt, (r, r)) < r - 5]

            @self.debug_img
            def lines_key_points_in_canny_edges():
                return cv.drawKeypoints(
                    curr_edges,
                    curr_kp,
                    None,
                    (0, 0, 0xFF))

            curr_kp, curr_des = self.bd.compute(curr_edges, curr_kp)

            last = self.last_minimap
            self.last_minimap = curr, curr_edges, curr_kp, curr_des

            if last is None:
                logger.info("No previous minimap to compare to")
                return False

            last_img, last_edges, last_kp, last_des = last

            bf =  cv.line_descriptor_BinaryDescriptorMatcher()

            matches = bf.match(last_des, curr_des)
            good = [m for m in matches if m.distance < 50]

            @self.debug_img
            def lines_matches():
                return cv.drawMatches(
                    last_img.rgb,
                    last_kp,
                    curr.rgb,
                    curr_kp,
                    good,
                    None,
                    flags=cv.DrawMatchesFlags_NOT_DRAW_SINGLE_POINTS)

            if len(good) < 8:
                logger.info(
                    "Did not find enough good matches, %d %d",
                    len(matches),
                    len(good))
                return False

            src_pts = np.float32(
                [last_kp[m.queryIdx].pt for m in good]).reshape(-1, 1, 2)
            dst_pts = np.float32(
                [curr_kp[m.trainIdx].pt for m in good]).reshape(-1, 1, 2)

            return src_pts, dst_pts

    def get_translation(self, img, src_pts, dst_pts):
        M, mask = cv.findHomography(src_pts, dst_pts, cv.RANSAC, 5.0)
        if M is None:
            logger.info(
                "Did not find Transformation Matrix",
                len(matches),
                len(good))
            return None

        matchesMask = mask.ravel().tolist()
        h, w, d = img.shape
        pts = np.float32([[0, 0], [0, h - 1], [w - 1, h - 1],
                          [w - 1, 0]]).reshape(-1, 1, 2)
        dst = cv.perspectiveTransform(pts, M)

        theta = angle_from_rot_matrix(M)

        logger.debug("Translation Matrix: %r", M)
        logger.debug("Translation Points: %r", dst)
        logger.debug("Translation Angle: %r", theta)
        return False

    def parse_minimap_others(self, curr):
        pass
        # curr_gray[~cm] = 0x81

        # curr_gray=cv.fastNlMeansDenoising(curr_gray, 30, 7, 11, )
        # curr_gray = cv2.blur(curr_gray, (3, 3))

        # curr_edges=cv2.Canny(curr_gray, 100, 200)

        # curr_edges[cm] = 0

        # sharpen_kernel = np.array([[-1,-1,-1,],[-1,9,-1,],[-1,-1,-1,]])
        # curr_gray = cv2.filter2D(curr_gray, -1, sharpen_kernel)

        # curr_gray = curr_gray // 32
        # curr_gray = curr_gray * 32

        # cv2.imshow("Canny",  curr_edges)

        # kp = cv.FastFeatureDetector_create().detect(curr_edges,None)
        # edges_points = cv.drawKeypoints(edges, kp, None, (0,0,0xFF), cv.DRAW_MATCHES_FLAGS_DRAW_RICH_KEYPOINTS)
        # cv2.imshow("Fast Features in Canny",  edges_points)

        # curr_rgb_edges = numpy.zeros_like(curr_rgb)
        # curr_rgb_edges[curr_edges == 0] = 0xFF, 0xFF, 0xFF
        # cv2.imshow("curr_rgb_edges", curr_rgb_edges)
        # cv2.waitKey()

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
