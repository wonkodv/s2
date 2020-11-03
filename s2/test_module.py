import unittest
from unittest.mock import Mock

from .module import *

class TestStuff(unittest.TestCase):
    def test_do_stuff(self):
        assert None == do_stuff(Mock(),Mock())

