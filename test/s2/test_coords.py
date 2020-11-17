import random

from pytest import approx

from s2.coords import AbsolutePosition, RelativePosition


def test_to_relative():
    abs = AbsolutePosition(1.1, 0.3, 0.1)

    rel2048 = abs.relative("map2048x2048")

    assert rel2048.x == approx(1551.3)
    assert rel2048.y == approx(815.1)
    assert rel2048.heading == 0.1
    assert rel2048.frame == "map2048x2048"


def test_to_abs():
    heading = object()
    rel = RelativePosition(717, 70, heading, "crop1015x680")
    abs = rel.absolute()
    assert abs.heading is heading
    assert abs.x == approx(1.0)
    assert abs.y == approx(0)

    rel = RelativePosition(196, 618, ..., "crop1015x680")
    abs = rel.absolute()
    assert abs.x == approx(0)
    assert abs.y == approx(1.0)


def test_chain():
    x = random.random()
    y = random.random()
    a = AbsolutePosition(x, y, 0)

    a2 = a.relative("crop1015x680").absolute().relative("map2048x2048").absolute()

    assert a2.x == approx(x)
    assert a2.y == approx(y)
