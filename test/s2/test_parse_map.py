from pathlib import Path

from s2.parse_map import parse_map
from s2.util import IMG

p = Path(__file__).parent


def test_parse_map():
    i = IMG.from_path(p / "map_with_arrow.png")
    pos = parse_map(i)

    assert pos.x == 314
    assert pos.y == 379
    assert 0.84 < pos.heading < 0.85


def test_parse_map_no_arrow():
    i = IMG.from_path(p / "map_without_arrow.png")
    pos = parse_map(i)

    assert pos is None
