from s2.coords import RelativePosition
from s2.config import get_config

import typing

import toml


class PointOfInterest(typing.NamedTuple):
    position: RelativePosition
    icon: str
    description:str = ""
    link: str = ""


def load_pois():

    pois = []

    for f in get_config("gui","poi_files"):
        d = toml.load(f)
        for p in d['POIs']:
            p['position'] = RelativePosition.from_string(p['position'])
            pois.append(PointOfInterest(**p))
    return pois   

