#!/bin/python

import PIL.Image
import numpy


def stitch():
    img = numpy.zeros((32 * 256, 32 * 256, 3), dtype=numpy.uint8)
    for x in range(32):
        for y in range(32):
            i = PIL.Image.open(f"{x:02d}x{y:02d}.jpg")
            n = numpy.asarray(i)
            Y = y * 256
            X = x * 256
            img[Y : Y + 256, X : X + 256] = n
            print(n.shape)
    return img
