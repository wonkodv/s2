import tkinter
import queue
import math


from .util import *


COLORS = {
    "PLAYER": "orange",
}


class GUI:
    def __init__(self, config):
        self.config = config
        self.root = tkinter.Tk()
        self.root.title("Second Screen ")
        self.root.bind("<Configure>", self.resize)
        self.root.state("zoomed")
        self.frame = f = tkinter.Frame(self.root)
        f.pack(fill=tkinter.BOTH, expand=True)

        self.canvas = c = tkinter.Canvas(self.frame, bg="grey")
        c.pack(fill=tkinter.BOTH, expand=True)
        # c.bind("<MouseWheel>", lambda evt:c.scale(tkinter.ALL, evt.x, evt.y, 1.001 ** evt.delta, 1.001 ** evt.delta))
        # c.bind('<ButtonPress-1>', lambda event: c.scan_mark(event.x, event.y))
        # c.bind("<B1-Motion>", lambda event: c.scan_dragto(event.x, event.y, gain=1))

        self.map_image = IMG.from_path("map.png")

        self.map_widget = c.create_image(
            -2200, -2000, anchor="nw", image=self.map_image.photoimage
        )
        self.player_widget = c.create_line(
            100, 100, 150, 150, arrow=tkinter.LAST, fill=COLORS["PLAYER"], width=5
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

        player_x = u.x
        player_y = u.y

        center_x = self.frame.winfo_width() // 2
        center_y = self.frame.winfo_height() // 2

        arrow_x = center_x + 20 * math.sin(u.alpha)
        arrow_y = center_y - 20 * math.cos(u.alpha)

        self.canvas.coords(self.player_widget, (center_x, center_y, arrow_x, arrow_y))

        map_x = center_x - player_x
        map_y = center_y - player_y

        self.canvas.coords(self.map_widget, (map_x, map_y))
        self.canvas.pack()

    def send_update(self, u):
        self.q.put(u)


def create(config):
    g = GUI(config)
    return g, g.send_update
