import logging
import math
import queue
import sys
import tkinter

from s2.config import get_config

from .util import IMG

logger = logging.getLogger(__name__)


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

        self.q = queue.Queue()
        self.root.after(100, self._process_q)

    def run(self):
        self.root.mainloop()

    def _process_q(self):
        try:
            while True:
                u = self.q.get_nowait()
                self.update(u)
        except queue.Empty:
            self.root.after(100, self._process_q)

    def resize(self, evt):
        self.canvas.pack()
        pass

    def update(self, u):
        assert u.id == "PLAYER"

        pos = u.position.relative(self.map_name)

        player_x = pos.x
        player_y = pos.y

        center_x = self.frame.winfo_width() // 2
        center_y = self.frame.winfo_height() // 2

        arrow_x = center_x + 50 * math.sin(pos.heading)
        arrow_y = center_y - 50 * math.cos(pos.heading)

        self.canvas.coords(self.player_widget, (center_x, center_y, arrow_x, arrow_y))

        map_x = center_x - player_x
        map_y = center_y - player_y

        self.canvas.coords(self.map_widget, (map_x, map_y))
        self.canvas.pack()

    def send_update(self, u):
        self.q.put(u)


def _handle_exception(tk, typ, val, tb):
    logger.exception("Exception in TK", exc_info=val)
    if typ is KeyboardInterrupt:
        sys.exit()


tkinter.Tk.report_callback_exception = _handle_exception


def create():
    g = GUI()
    return g, g.send_update
