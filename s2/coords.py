"""Work with coordinates in different image resolutions and cropped areas.

The Reference Points are the most NorthWestern grey pixel in the parking Lot
and  the most SouthEastern one on the pier.
"""

import typing

REF_POINTS = {
    "map8192x8192": ((1793, 1991), (5809, 6223)),
    "map2048x2048": ((448, 498), (1451, 1555)),
    "crop1015x680": ((196, 70), (717, 618)),
}


class AbsolutePosition(typing.NamedTuple):
    x: float
    y: float
    heading: float

    def relative(self, frame) -> "RelativePosition":
        """Absolute Position.

        Given as offset to Reference Point 1 as fraction of the distance between reference points
        1 and 2.
        """
        ref_points = REF_POINTS[frame]

        (ref1_x, ref1_y), (ref2_x, ref2_y) = ref_points

        scale_x = ref2_x - ref1_x
        scale_y = ref2_y - ref1_y

        x = self.x * scale_x + ref1_x
        y = self.y * scale_y + ref1_y

        return RelativePosition(x, y, self.heading, frame)


class RelativePosition(typing.NamedTuple):
    """Position as pixel coordinates in an image.

    Images has the dimensions `frame`
    Heading is in Radians from -Pi/2 to Pi/2
    """

    x: float
    y: float
    heading: float
    frame: tuple

    def absolute(self) -> AbsolutePosition:
        ref_points = REF_POINTS[self.frame]

        (ref1_x, ref1_y), (ref2_x, ref2_y) = ref_points

        scale_x = ref2_x - ref1_x
        scale_y = ref2_y - ref1_y

        x = (self.x - ref1_x) / scale_x
        y = (self.y - ref1_y) / scale_y
        return AbsolutePosition(x, y, self.heading)

    def round(self):
        return int(self.x), int(self.y)
