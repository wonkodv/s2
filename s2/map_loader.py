#!/usr/bin/python -u
""" Download the gta map."""

import concurrent.futures
import io
import sys
import typing

import numpy
import PIL.Image
import requests

TILE_RESOLUTION = 256


class Scale(typing.NamedTuple):
    index: int

    @property
    def tiles_per_axis(self):
        return 2 ** self.index

    @property
    def resolution(self):
        return TILE_RESOLUTION * self.tiles_per_axis


assert Scale(5).tiles_per_axis == 32
assert Scale(4).tiles_per_axis == 16


def get_image(x, y, scale):
    index = scale.tiles_per_axis * y + x + 1
    url = (
        f"https://media.gtanet.com/gta4/images/map/tiles/{scale.index}_{index:02d}.jpg"
    )
    img_data = requests.get(url).content
    img_io = io.BytesIO(img_data)
    return PIL.Image.open(img_io)


def main(scale="2"):
    scale = Scale(int(scale))

    img = numpy.zeros((scale.resolution, scale.resolution, 3), dtype=numpy.uint8)

    tile_coords = [
        (x, y) for x in range(scale.tiles_per_axis) for y in range(scale.tiles_per_axis)
    ]

    with concurrent.futures.ThreadPoolExecutor(max_workers=5) as threadpool:
        tiles = threadpool.map(
            lambda coord: (coord, get_image(*coord, scale)),
            tile_coords,
        )
        for (x, y), tile in tiles:
            print(f"stitching {x}-{y}")
            x = x * TILE_RESOLUTION
            y = y * TILE_RESOLUTION
            img[y : y + TILE_RESOLUTION, x : x + TILE_RESOLUTION] = tile

    print(f"saving {x}-{y}")
    PIL.Image.fromarray(img).save(f"map{scale.resolution}x{scale.resolution}.png")


if __name__ == "__main__":
    sys.exit(main(*sys.argv[1:]))
