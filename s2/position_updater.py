""" Update Player position by looking at the minimap. """

import datetime
import functools
import logging
import math
import time

import cv2
import numpy
import numpy.linalg
import PIL.Image

import s2.parse_map
from s2.coords import RelativePosition
from s2.get_image import get_image
from s2.util import IMG, Update

COORDS = {
    (1920, 1080): {
        "minimap_center": (918, 209),
        "minimap_radius": 80,
    }
}


NOT_A_MINIMAP = "NOT A MINIMAP"

logger = logging.getLogger(__name__)

numpy.set_printoptions(formatter={"float": "{:.3f}".format})


@functools.lru_cache
def circle_mask(shape, center=None, radius=None):
    if not center:
        center = shape[0] // 2, shape[1] // 2
    if not radius:
        radius = min(*center)
    h, w = shape[:2]
    Y, X = numpy.ogrid[:h, :w]
    dist_from_center = numpy.sqrt((X - center[0]) ** 2 + (Y - center[1]) ** 2)
    mask = dist_from_center <= radius
    return mask


class PositionUpdater:
    last_minimap = None
    _debug_path = None
    _debug_wait_key = None

    def __init__(self, config, send_update):
        self.config = config
        self.send_update = send_update

        self.position = RelativePosition(
            3100, 2600, 0, certainty=0, frame="Map8192x8192"
        )
        self.updates_since_last_fix = 0
        self.init = False
        self._map_feature_cache = {}

    def stop(self):
        self._running = False

    def _init(self):
        if self.init:
            return
        self.init = True
        self.map_edges = numpy.array(PIL.Image.open("map_edges.png"))

        self.akaze = cv2.AKAZE_create()
        self.dm = cv2.DescriptorMatcher_create(cv2.DescriptorMatcher_BRUTEFORCE_HAMMING)

    def run(self):
        logger.info("Starting Screen Grabbing")
        self._init()
        self._running = True
        while self._running:
            time.sleep(0)
            self.update()

    def update(self):
        img = get_image()

        if not img:
            return

        self.updates_since_last_fix += 1

        if self.config["debug"]["save_images"]:
            self._debug_format = dict(
                time=time.time(),
                datetime=datetime.datetime.now(),
            )

        position = self.parse_image(img)

        if not position:
            return

        if not self.validate_update(position):
            return

        self.updates_since_last_fix = 0

        dist = math.dist(self.position[:2], position[:2])

        logger.info(
            "Position moved %f: %r",
            dist,
            position,
        )
        u = Update(position, "PLAYER")

        self.send_update(u)
        self.position = position

    def validate_update(self, pos):
        if pos.certainty >= 1:
            return True
        dist = math.dist(self.position[:2], pos[:2])

        if dist > 500 * pos.certainty:  # no hardcoded Values
            logger.info(
                "Discarded moved %f %r",
                dist,
                pos,
            )
            return False
        return True

    def debug_img(self, function):
        if not self.config["debug"]["save_images"]:
            return
        name = function.__name__
        path = self.config["debug"]["save_images"].get(name)
        if not path:
            return
        img = function()
        p = path.format(**self._debug_format)
        if isinstance(img, IMG):
            img.image.save(p)
        else:
            PIL.Image.fromarray(img).save(p)

    def parse_image(self, img):
        @self.debug_img
        def screenshot():
            return img

        position = self.parse_minimap(img)

        if position is NOT_A_MINIMAP:
            position = self.parse_map(img)

        return position

    def parse_map(self, img):
        relPos = s2.parse_map.parse_map(img)
        if relPos:
            a = relPos.absolute()
            r2 = a.relative("map8192x8192")
            logger.debug("Using Position from Map: %r", r2)
            return r2

    def map_features(self):
        x, y = self.position.round()

        # TODO: add based on speed and heading ?
        groups = 64  # cach features for 64 by 64 pixel blocks.
        box_size = 512

        x |= groups - 1
        y |= groups - 1

        slices = (
            slice(y - box_size // 2 - groups // 2, y + box_size // 2 - groups // 2),
            slice(x - box_size // 2 - groups // 2, x + box_size // 2 - groups // 2),
        )

        key = x, y
        features = self._map_feature_cache.get(key)
        if features is None:
            features = self.akaze.detectAndCompute(self.map_edges[slices], None)
            self._map_feature_cache[key] = features

        return features, slices

    def parse_minimap(self, img):
        coords = COORDS[(img.width, img.height)]
        cx, cy = coords["minimap_center"]
        r = coords["minimap_radius"]

        minimap = IMG(rgb=img.rgb[cx - r : cx + r, cy - r : cy + r, :])

        a = self.get_minimap_arrow(minimap)
        if a is None:
            return NOT_A_MINIMAP

        # outer_mask = circle_mask(shape)
        # inner_mask = circle_mask(shape, radius=15)
        # mask = ~(inner_mask & outer_mask)
        # https://docs.opencv.org/master/db/d70/tutorial_akaze_matching.html
        minimap_keypoints, minimap_descriptors = self.akaze.detectAndCompute(
            minimap.edges,
            None,  # TODO: Mask
        )

        (map_keypoints, map_descriptors), offset_slices = self.map_features()

        offset = numpy.array([offset_slices[1].start, offset_slices[0].start])

        matches = self.dm.knnMatch(minimap_descriptors, map_descriptors, 2)
        good = [m for m, n in matches if m.distance < 0.8 * n.distance]

        # TODO: calculate center of good, then filter map_features by distance
        # and match again

        if len(good) < 6:

            @self.debug_img
            def minimap_with_too_few_matches():
                box = self.map_edges[offset_slices].copy()
                op = tuple(numpy.array(self.position[:2]) - offset)
                cv2.circle(box, op, 5, (0x00, 0x00, 0xFF), 1)
                return cv2.drawMatches(
                    minimap.rgb,
                    minimap_keypoints,
                    box,
                    map_keypoints,
                    good,
                    None,
                    flags=cv2.DrawMatchesFlags_NOT_DRAW_SINGLE_POINTS,
                )

            logger.debug(
                "Did not find enough good matches, %d %d", len(matches), len(good)
            )
            return False

        src_pts = numpy.float32(
            [minimap_keypoints[m.queryIdx].pt for m in good],
        ).reshape(-1, 1, 2)
        dst_pts = numpy.float32(
            [map_keypoints[m.trainIdx].pt for m in good],
        ).reshape(-1, 1, 2)

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

        heading = -math.atan2(M[0, 1], M[0, 0])

        @self.debug_img
        def minimap_with_matches():

            arrow = [minimap.width / 2, 0, 1]
            arrow = M @ arrow
            arrow /= arrow[2]
            arrow = arrow[:2]

            arrow.clip(0, 512)

            arrow = int(arrow[0]), int(arrow[1])
            bc = tuple(numpy.uint32(position_in_box))
            op = tuple(numpy.array(self.position[:2]) - offset)

            box = self.map_edges[offset_slices].copy()

            cv2.arrowedLine(box, bc, arrow, (0x00, 0xFF, 0xFF), 1)

            cv2.circle(box, op, 5, (0x00, 0x00, 0xFF), 1)
            return cv2.drawMatches(
                minimap.rgb,
                minimap_keypoints,
                box,
                map_keypoints,
                good,
                None,
                flags=cv2.DrawMatchesFlags_NOT_DRAW_SINGLE_POINTS,
            )

        logger.debug(
            "Position based on Minimap: %.1f %.1f %.1f°", *pos, math.degrees(heading)
        )
        pos = RelativePosition(
            *pos,
            heading,
            certainty=0.5,
            frame="map8192x8192",
        )
        return pos

    def get_translation(self, img, src_pts, dst_pts):
        M, mask = cv2.findHomography(
            src_pts,
            dst_pts,
            cv2.RANSAC,
            2,
            None,
            1000,
            0.999,
        )
        return M

    def get_minimap_arrow(self, mm):
        """Look for the Minimap Arrow.

        Finds contours of white area, approximates a Poly and selects one that
        is in the middle of the map and has 3 corners.
        """
        h, w = mm.height, mm.width

        _, v = cv2.threshold(mm.gray, 0xDA, 255, cv2.THRESH_BINARY)
        contours, hierarchy = cv2.findContours(
            v,
            cv2.RETR_TREE,
            cv2.CHAIN_APPROX_SIMPLE,
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
            logger.debug("Not a Minimap")
            return None


def create(config, send_update):
    return PositionUpdater(config, send_update)
