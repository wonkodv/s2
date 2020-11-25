import typing
from pathlib import Path
import toml

from s2.config import get_config
from s2.coords import RelativePosition


class PointOfInterest(typing.NamedTuple):
    position: RelativePosition
    group: str
    icon: str = None
    description: str = None
    link: str = None

    @classmethod
    def from_dict(cls, d):
        position = RelativePosition.from_string(d["position"])
        if "icon" in d:
            icon = d["icon"]
        else:
            icon = d["group"]
        return cls(position, d["group"], icon, d.get("description"), d.get("link"))

    def to_dict(self):
        d = dict(
            position=str(self.position),
            group=self.group,
        )
        if self.icon and self.icon != self.group:
            d["icon"] = self.icon
        if self.description:
            d["description"] = self.description
        if self.link:
            d["link"] = self.link
        return d


def load_pois():

    pois = []

    for f in get_config("gui", "poi_files"):
        if Path(f).is_file():
            d = toml.load(f)
            for p in d["POIs"]:
                if get_config("gui", "enabled_groups").get(p["group"], True):
                    pois.append(PointOfInterest.from_dict(p))
    return pois
