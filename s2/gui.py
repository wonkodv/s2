import functools
import logging
import math
import sys
import tkinter
import toml
import datetime
import time
import PIL.Image
import PIL.ImageTk
import pathlib

from s2.config import get_config
from s2.pois import load_pois, PointOfInterest
from s2.get_image import get_image

from .util import IMG

try:
    import hotkey
except ImportError:
    pass
else:
    hotkey.start()

logger = logging.getLogger(__name__)


@functools.cache
def load_icon(ico):
    """Load icon with name.

    By caching, the same image is not loaded twice AND a reference to the
    photo image is kept which is importnt because Canvas.create_image does not
    and will not show the image, without an error if the reference to the
    PhotoImage goes stale.
    """
    return PIL.ImageTk.PhotoImage(PIL.Image.open(f"icons/{ico}.png"))


class GUI:
    def __init__(self):
        self.root = tkinter.Tk()
        self.root.title("Second Screen ")
        self.root.bind("<Configure>", self.resize)
        try:
            self.root.state("zoomed")
        except tkinter.TclError:
            pass

        self.frame = f = tkinter.Frame(self.root)
        f.pack(fill=tkinter.BOTH, expand=True)

        self.canvas = c = tkinter.Canvas(self.frame, bg="grey")
        c.pack(fill=tkinter.BOTH, expand=True)
        # c.bind("<MouseWheel>", lambda evt:c.scale(tkinter.ALL, evt.x, evt.y, 1.001 ** evt.delta, 1.001 ** evt.delta))
        # c.bind('<ButtonPress-1>', lambda event: c.scan_mark(event.x, event.y))
        # c.bind("<B1-Motion>", lambda event: c.scan_dragto(event.x, event.y, gain=1))

        self.map_name = get_config("gui", "map")
        self.map_image = IMG.from_path(f"{self.map_name}.png")

        self.map_widget = c.create_image(
            -0, -0, anchor="nw", image=self.map_image.photoimage
        )

        self.player_widget = c.create_line(
            100,
            100,
            150,
            150,
            arrow=tkinter.LAST,
            fill=get_config("gui", "colors", "player"),
            width=10,
        )

        self.pois = []
        for poi in load_pois():
            self.add_poi(poi)

        self.hotkeys = []
        hk = get_config("gui", "screenshot", "hotkey")
        if hk:
            self.hotkeys.append(
                hotkey.HotKey(
                    hk,
                    self.root.after,
                    1,
                    self.create_poi_screenshot,
                )
            )
        for hk in self.hotkeys:
            hk.register()

    def add_poi(self, poi):
        rel = poi.position.relative(self.map_name)
        wdg = self.canvas.create_image(
            rel.x,
            rel.y,
            anchor="nw",
            image=load_icon(poi.icon),
        )
        self.pois.append((poi, wdg))

    def run(self):
        self.root.mainloop()

    def resize(self, evt):
        self.canvas.pack()
        pass

    def update(self, u):
        assert u.id == "PLAYER"

        self.most_recent_position = u.position

        pos = u.position.relative(self.map_name)

        player_x, player_y = pos.round()

        center_x = self.frame.winfo_width() // 2
        center_y = self.frame.winfo_height() // 2

        arrow_x = center_x + 50 * math.sin(pos.heading)
        arrow_y = center_y - 50 * math.cos(pos.heading)

        self.canvas.coords(self.player_widget, (center_x, center_y, arrow_x, arrow_y))

        map_x = center_x - player_x
        map_y = center_y - player_y

        self.canvas.coords(self.map_widget, (map_x, map_y))

        # breakpoint()
        for poi, wdg in self.pois:
            x, y = poi.position.relative(self.map_name).round()
            draw_x, draw_y = x + map_x, y + map_y
            self.canvas.coords(wdg, (draw_x, draw_y))

        self.canvas.pack()

    def send_update(self, u):
        self.root.after(1, self.update, u)

    def create_poi_screenshot(self):
        lg = logging.getLogger(self.__class__.__qualname__).getChild(".screenshot")
        img = get_image()
        if not img:
            lg.warning("Can not get Image")
            return

        pos = self.most_recent_position
        d = datetime.datetime.now()
        t = time.time()

        fn = get_config("gui", "screenshot", "image")
        fn = fn.format(pos=pos, time=t, datetime=d)
        pathlib.Path(fn).parent.mkdir(parents=True, exist_ok=True)

        desc = get_config("gui", "screenshot", "description")
        desc = desc.format(pos=pos, time=t, datetime=d)

        lg.info("Saving Screenshot %s", fn)
        img.image.save(fn)

        poi = PointOfInterest(
            position=pos,
            group=get_config("gui", "screenshot", "group"),
            icon=get_config("gui", "screenshot", "icon"),
            description=desc,
            link=fn,
        )
        self.add_poi(poi)

        t = toml.dumps(dict(POIs=[poi]))

        fn = get_config("gui", "screenshot", "poi_file")
        pathlib.Path(fn).parent.mkdir(parents=True, exist_ok=True)

        lg.info("Appending poi to file %s %r", fn, poi)
        s = toml.dumps(dict(POIs=[poi.to_dict()]))
        with open(fn, "at") as f:
            f.write("\n\n")
            f.write(s)


def _handle_exception(tk, typ, val, tb):
    logger.exception("Exception in TK", exc_info=val)
    if typ is KeyboardInterrupt:
        sys.exit()


tkinter.Tk.report_callback_exception = _handle_exception


def create():
    g = GUI()
    return g, g.send_update
