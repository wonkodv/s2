"""Get the Points of interest form gta4.net."""

import json
import re

import requests
import toml

s = requests.get("https://www.gta4.net/map/map.js").text
s = s.partition("module.exports=")[2]
s = s.partition("},{}],2:[function(require,module,exports){module.expo")[0]

pois = json.loads(s)


POIs = []

for category in pois:
    for p in pois[category]:
        poi = dict()
        POIs.append(poi)
        poi["icon"] = category
        x = float(p["lng"])
        y = float(p["lat"])
        poi["position"] = f"gta4.net:{x}:{y}"

        if category == "pigeon":
            poi["link"] = p["img"].replace("\\", "")

        if category == "weapon":
            # poi['icon'] = re.sub(r'Weapon \((.*)\)',"\\1",p['label']   )
            poi["description"] = re.sub("<[^>]*>", "\n", p["text"]).strip()

        if category == "stunt":
            poi["link"] = p["vid"].replace("\\", "")

        if category == "platform":
            poi["link"] = p["img"].replace("\\", "")

        if category == "theft":
            poi["description"] = re.sub(
                r"<h2>(.*)</h2>.*<strong>(.*)</strong>\.</p>", "\\1\n\\2", p["text"]
            )

        if category == "character":
            poi["description"] = re.sub("<[^>]*>", "\n", p["text"]).strip()
            poi["link"] = p["img"]

        if category == "activities":
            poi["icon"] = p["icon"]

with open("pois.toml", "wt") as f:
    toml.dump(dict(POIs=POIs), f)
