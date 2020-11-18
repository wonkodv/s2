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
    polys = [cv2.approxPolyDP(c, 2, True) for c in contours]
    return polys


def get_arrow(poly):
    if len(poly) != 4:
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

    if long1_length < 19 or long2_length < 19:
        logger.warning("long lines too short", lines)
        return None
    if long1_length > 23 or long2_length > 23:
        logger.warning("long lines too long", lines)
        return None

    if long1_start == long2_end:
        stem = poly[long1_start]
    elif long1_end == long2_start:
        stem = poly[long1_end]
    else:
        logger.warning("Arrow long Lines are not connected start to end %r", lines)
        return None

    if short1_length < 9 or short2_length < 9:
        logger.warning("Short lines too short", lines)
        return None
    if short1_length > 13 or short2_length > 13:
        logger.warning("Short lines too long", lines)
        return None

    if short1_start == short2_end:
        stern = poly[short1_start]
    elif short1_end == short2_start:
        stern = poly[short1_end]
    else:
        logger.warning("Arrow short Lines are not connected start to end %r", lines)
        return None

    direction = stem - stern
    angle = math.atan2(*direction)

    return stern, angle


def parse_map(img):
    rgb = crop_image(img.rgb)
    hsv = cv2.cvtColor(rgb, cv2.COLOR_BGR2HSV)  # TODO: is img.rgb really BGR?
    mask = cv2.inRange(hsv, (100, 255, 150), (100, 255, 240))
    polygons = polygons_in_mask(mask)

    arrow = (get_arrow(p) for p in polygons)
    arrow = [a for a in arrow if a]
    if len(arrow) != 1:
        if len(arrow) > 1:
            logger.warning("More than 1 Arrow: %r", arrow)
        else:
            logger.debug("Not a Map or Arrow not visible")
        return None

    (y, x), angle = arrow[0]

    height, width = rgb.shape[:2]
    frame_of_reference = f"crop{width}x{height}"

    return RelativePosition(
        x=x,
        y=y,
        heading=angle,
        certainty=1,
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
