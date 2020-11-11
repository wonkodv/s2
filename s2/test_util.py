import pytest

from .util import merge_recursive_dict

### Merge dict

old = dict(
    a="old a",
    b="old b",
    d=dict(
        a="old d a",
        b="old d b",
    ),
)
new = dict(
    a="new a",
    c="new c",
    d=dict(
        a="new d a",
        c="new d c",
    ),
)


def test_merge_dict_recursive():
    merged = merge_recursive_dict(old, new)
    expected = dict(
        a="new a",
        b="old b",
        c="new c",
        d=dict(
            a="new d a",
            b="old d b",
            c="new d c",
        ),
    )
    assert merged == expected


def test_merge_dict_type_mismatch():
    with pytest.raises(TypeError):
        merge_recursive_dict(dict(a=1), dict(a={}))
