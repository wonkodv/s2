import random

from pytest import approx

from s2.coords import RelativePosition, _AbsolutePosition


def test_to_relative():
    abs = _AbsolutePosition(1.1, 0.3, 0.1)

    rel2048 = abs.relative("map2048x2048")

    assert rel2048.x == approx(1551.3)
    assert rel2048.y == approx(815.1)
    assert rel2048.heading == 0.1
    assert rel2048.frame == "map2048x2048"


def test_to_abs():
    heading = object()
    rel = RelativePosition(717, 70, heading, "crop1015x680")
    abs = rel._absolute()
    assert abs.heading is heading
    assert abs.x == approx(1.0)
    assert abs.y == approx(0)

    rel = RelativePosition(196, 618, ..., "crop1015x680")
    abs = rel._absolute()
    assert abs.x == approx(0)
    assert abs.y == approx(1.0)


def test_chain():
    x = random.random()
    y = random.random()
    a = _AbsolutePosition(x, y, ...)

    a2 = a.relative("crop1015x680").relative("map2048x2048")._absolute()

    assert a2.x == approx(x)
    assert a2.y == approx(y)


def test_from_string():
    r = RelativePosition(123, 456, 7, "Frame")
    s = str(r)
    r2 = RelativePosition.from_string(s)

    assert r == r2
