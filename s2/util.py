import collections
import collections.abc
import logging
import sys
from functools import cached_property

import cv2
import numpy
import PIL.Image
import PIL.ImageGrab
import PIL.ImageTk

if sys.version_info < (3, 9):
    from functools import lru_cache as cache  # TODO: move to python 3.9?
else:
    from functools import cache


logger = logging.getLogger(__name__)

Update = collections.namedtuple("Update", "position id")


class IMG:
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

    @classmethod
    @cache
    def from_path(cls, p):
        return cls(image=PIL.Image.open(p))

    @classmethod
    def from_rgb(cls, rgb):
        return cls(rgb=rgb)

    @classmethod
    def from_image(cls, image):
        return cls(image=image)

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

    @cached_property
    def gray(self):
        return cv2.cvtColor(self.rgb, cv2.COLOR_RGB2GRAY)

    @cached_property
    def smooth(self):
        return cv2.fastNlMeansDenoising(self.gray, 30, 7, 11)

    @cached_property
    def edges(self):
        return cv2.Canny(self.gray, 100, 200)

    @cached_property
    def photoimage(self):
        return PIL.ImageTk.PhotoImage(self.image)


def merge_recursive_dict(old, new):
    """Merge two dictionaries recursively.

    Produces a Tree of new dictionaries, at each level values from new overwrite
    values from old.
    Fails if for the same key one as a dict and the other something else.
    If one has a dictionary for a key and the other has no entry, that dict
    becomes part of the tree without copy.

    """
    old_is_dict = isinstance(old, collections.abc.Mapping)
    new_is_dict = isinstance(new, collections.abc.Mapping)

    if old_is_dict and new_is_dict:
        keep = old.keys() - new.keys()
        add = new.keys() - old.keys()
        merge = new.keys() & old.keys()

        return dict(
            (
                *((k, old[k]) for k in keep),
                *((k, new[k]) for k in add),
                *((k, merge_recursive_dict(old[k], new[k])) for k in merge),
            )
        )
    elif not old_is_dict and not new_is_dict:
        return new
    else:
        raise TypeError("Either both or neither arguments must be dicts", old, new)
