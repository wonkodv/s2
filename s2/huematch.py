import pathlib
import cv2
import cv2 as cv
import numpy as np

cwd = pathlib.Path.cwd()

bgr = cv2.cvtColor(numpy.array(rgb), cv2.COLOR_RGB2BGR)
hsv = cv2.cvtColor(src, cv2.COLOR_BGR2HSV)
ch = (0, 0)
hue = np.empty(hsv.shape, hsv.dtype)
cv2.mixChannels([hsv], [hue], (0,0))


cv2.namedWindow("Hans")
cv2.imshow("Hans", hue)