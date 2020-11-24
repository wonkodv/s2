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
    "gta4.net": ((-100, 46), (76, -47.5)), # TODO: find this out exactly !
}


class _AbsolutePosition(typing.NamedTuple):
    x: float
    y: float
    heading: float

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

        return RelativePosition(x, y, self.heading, frame)

    def _absolute(self) -> "_AbsolutePosition":
        return self


class RelativePosition(typing.NamedTuple):
    """Position as pixel coordinates in an image.

    Images has the dimensions `frame`
    Heading is in Radians from -Pi/2 to Pi/2
    """

    x: float
    y: float
    heading: float
    frame: tuple

    def _absolute(self) -> _AbsolutePosition:
        ref_points = REF_POINTS[self.frame]

        (ref1_x, ref1_y), (ref2_x, ref2_y) = ref_points

        scale_x = ref2_x - ref1_x
        scale_y = ref2_y - ref1_y

        x = (self.x - ref1_x) / scale_x
        y = (self.y - ref1_y) / scale_y
        return _AbsolutePosition(x, y, self.heading)

    def round(self):
        return int(self.x), int(self.y)

    def relative(self, frame) -> "RelativePosition":
        if frame == self.frame:
            return self
        return self._absolute().relative(frame)

    @classmethod
    def from_string(cls, s):
        parts = s.split(":")
        if len(parts) == 3:
            frame, x, y = parts
            heading = 0
        elif len(parts) == 4:
            frame, x, y, heading = parts
        else:
            raise ValueError(
                "Expecting 3 (frame:x:y) or 4 (frame:x:y:heading) elements", parts
            )
        return cls(x=float(x), y=float(y), heading=float(heading), frame=frame)

    def __str__(self):
        return f"{self.frame}:{self.x:f}:{self.y:f}:{self.heading:f}"

    def __repr__(self):
        heading = math.degrees(self.heading)
        return f"{self.__class__.__name__}({self.x:.0f}, {self.y:.0f}, {heading:.0f}°, {self.frame})"
