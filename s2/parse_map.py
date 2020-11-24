import logging
import math

import cv2
import numpy.linalg

from s2.coords import RelativePosition

logger = logging.getLogger(__name__)


COORDS = {
    (1920, 1080): {
        "area_of_interest": [475, 208, 1490, 888],
    }
}


def crop_image(array):
    height, width = array.shape[:2]
    left, top, right, bottom = COORDS[width, height]["area_of_interest"]
    return array[top:bottom, left:right]


def polygons_in_mask(mask):
    contours, hierarchy = cv2.findContours(
        mask,
        cv2.RETR_EXTERNAL,
        cv2.CHAIN_APPROX_NONE,
    )
    polys = [cv2.approxPolyDP(c, 4, True) for c in contours]
    return polys


def get_arrow(poly):
    if len(poly) != 4:
        logger.debug("Not 4 points: %r", poly)
        return None

    poly = poly.reshape(4, 2)

    lines = sorted(
        (numpy.linalg.norm(poly[i] - poly[i - 1]), i, (i - 1) % 4) for i in range(4)
    )

    (
        (short1_length, short1_start, short1_end),
        (short2_length, short2_start, short2_end),
        (long1_length, long1_start, long1_end),
        (long2_length, long2_start, long2_end),
    ) = lines

    logger.debug("Lines: %r", lines)

    certainty = 1.0

    if long1_length < 15 or long2_length < 15:
        logger.warning("long lines too short %r", lines)
        certainty *= 0.9
    if long1_length > 23 or long2_length > 23:
        logger.warning("long lines too long %r", lines)
        certainty *= 0.9

    if long1_start == long2_end:
        stem = poly[long1_start]
    elif long1_end == long2_start:
        stem = poly[long1_end]
    else:
        logger.warning("Arrow long Lines are not connected start to end %r", lines)
        return None

    if short1_length < 7 or short2_length < 7:
        logger.warning("Short lines too short", lines)
        certainty *= 0.9
    if short1_length > 14 or short2_length > 14:
        logger.warning("Short lines too long", lines)
        certainty *= 0.9

    if short1_start == short2_end:
        stern = poly[short1_start]
    elif short1_end == short2_start:
        stern = poly[short1_end]
    else:
        logger.warning("Arrow short Lines are not connected start to end %r", lines)
        return None

    dx, dy = stem - stern
    angle = math.atan2(dx, -dy)

    return stern, angle, certainty


def parse_map(img):
    rgb = crop_image(img.rgb)
    hsv = cv2.cvtColor(rgb, cv2.COLOR_BGR2HSV)  # TODO: is img.rgb really BGR?
    mask = cv2.inRange(hsv, (100, 255, 150), (100, 255, 240))
    polygons = polygons_in_mask(mask)

    if not polygons:
        logger.debug("No polygons found")
    arrow = (get_arrow(p) for p in polygons)
    arrow = [a for a in arrow if a]
    if len(arrow) != 1:
        if len(arrow) > 1:
            logger.warning("More than 1 Arrow: %r", arrow)
        else:
            logger.debug("Not a Map or Arrow not visible")
        return None

    (x, y), angle, certainty = arrow[0]

    height, width = rgb.shape[:2]
    frame_of_reference = f"crop{width}x{height}"

    return RelativePosition(
        x=x,
        y=y,
        heading=angle,
        frame=frame_of_reference,
    )


def test(image="test/s2/map_with_arrow.png"):
    from s2.util import IMG

    def debug_(f):
        f()

    global debug
    debug = debug_

    logging.basicConfig(level=logging.DEBUG)

    logger.debug(image)

    img = IMG.from_path(image)
    pos = parse_map(img)
    print(pos)
    if pos:
        return 0
    return 1


if __name__ == "__main__":
    import sys

    sys.exit(test(*sys.argv[1:]))
