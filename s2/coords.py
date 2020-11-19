"""Work with coordinates in different image resolutions and cropped areas.

The Reference Points are the most NorthWestern grey pixel in the parking Lot
and  the most SouthEastern one on the pier.
"""

import math
import typing

REF_POINTS = {
    "map8192x8192": ((1793, 1991), (5809, 6223)),
    "map4096x4096": ((896, 995), (2904, 3111)),
    "map2048x2048": ((448, 498), (1451, 1555)),
    "crop1015x680": ((196, 70), (717, 618)),
}


class AbsolutePosition(typing.NamedTuple):
    x: float
    y: float
    heading: float
    certainty: float

    def relative(self, frame) -> "RelativePosition":
        """Relative Position.

        Pixel in the given `frame` of reference
        """
        ref_points = REF_POINTS[frame]

        (ref1_x, ref1_y), (ref2_x, ref2_y) = ref_points

        scale_x = ref2_x - ref1_x
        scale_y = ref2_y - ref1_y

        x = self.x * scale_x + ref1_x
        y = self.y * scale_y + ref1_y

        return RelativePosition(x, y, self.heading, self.certainty, frame)

    def absolute(self) -> "AbsolutePosition":
        return self


class RelativePosition(typing.NamedTuple):
    """Position as pixel coordinates in an image.

    Images has the dimensions `frame`
    Heading is in Radians from -Pi/2 to Pi/2
    """

    x: float
    y: float
    heading: float
    certainty: float
    frame: tuple

    def absolute(self) -> AbsolutePosition:
        ref_points = REF_POINTS[self.frame]

        (ref1_x, ref1_y), (ref2_x, ref2_y) = ref_points

        scale_x = ref2_x - ref1_x
        scale_y = ref2_y - ref1_y

        x = (self.x - ref1_x) / scale_x
        y = (self.y - ref1_y) / scale_y
        return AbsolutePosition(x, y, self.heading, self.certainty)

    def round(self):
        return int(self.x), int(self.y)

    def relative(self, frame) -> "RelativePosition":
        if frame == self.frame:
            return self
        return self.absolute().relative(frame)

    def __repr__(self):
        heading = math.degrees(self.heading)
        return f"{self.__class__.__name__}({self.x:.0f}, {self.y:.0f}, {heading:.0f}°, {self.frame})"
