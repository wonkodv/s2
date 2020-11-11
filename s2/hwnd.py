"""Functions that deal with Windows Windows."""

import collections
import ctypes
import re
import time
from ctypes import byref, c_wchar
from ctypes.wintypes import BOOL, DWORD, HWND, LPARAM, POINT, RECT

Rect = collections.namedtuple("Rect", "left,top,right,bottom,width,height")


class Window:
    # Placeholder for singleton Objects

    """NULL Window is used as "No Window" in find """
    NULL = 0

    """children of TOP are all Top-Level Windows"""
    TOP = 0

    """The Desktop Window"""
    DESKTOP = 1

    # Constructors

    def __init__(self, hwnd):
        if isinstance(hwnd, Window):
            hwnd = hwnd.hwnd
        if not isinstance(hwnd, int):
            raise TypeError("expected Int", hwnd)
        self.hwnd = hwnd

    @classmethod
    def get_foreground_window(cls):
        """Current Foreground Window."""
        return cls(ctypes.windll.user32.GetForegroundWindow())

    @classmethod
    def get_window_from_point(cls, p=None, main=False):
        """Window From Screen Coordinates or current Mouse Position."""
        if p is None:
            p = POINT()
            if not ctypes.windll.user32.GetCursorPos(byref(p)):
                raise ctypes.WinError()
        elif not isinstance(p, POINT):
            p = POINT(*p)
        w = ctypes.windll.user32.WindowFromPoint(p)
        w = cls(w)
        if main:
            p = w
            while p:
                w = p
                p = w.parent
        return w

    @classmethod
    def get_desktop_window(cls):
        """Desktop Window."""
        return cls(ctypes.windll.user32.GetDesktopWindow())

    # ParamClass methods

    @classmethod
    def complete(cls, s):
        yield "_MOUSE_POS_MAIN"
        yield "_MOUSE_POS"
        yield "_WAIT_FOREGROUND"
        yield "_FOREGROUND"
        for w in cls.TOP.children:
            yield w.class_name
            yield w.title

    @classmethod
    def convert(cls, s):
        if s == "_MOUSE_POS_MAIN":
            w = cls.get_window_from_point(main=True)
        elif s == "_MOUSE_POS":
            w = cls.get_window_from_point()
        elif s == "_FOREGROUND":
            w = cls.get_foreground_window()
        elif s == "_WAIT_FOREGROUND":
            w = org = cls.get_foreground_window()
            while w == org:
                time.sleep(0.1)
                w = cls.get_foreground_window()
        else:
            w = cls.TOP.find(s)
        if w:
            return w
        raise ValueError("No window", s)

    # Properties

    @property
    def class_name(self):
        """Name of the Win32 Window-Class."""
        name = (c_wchar * 1024)()
        if not ctypes.windll.user32.GetClassNameW(self.hwnd, name, len(name)):
            raise ctypes.WinError()
        return name.value

    @property
    def parent(self):
        """Parent of the Window."""
        return type(self)(ctypes.windll.user32.GetParent(self.hwnd))

    @parent.setter
    def parent(self, parent):
        """Set Parent of the Window."""
        if parent is None or parent == 0:
            parent = self.TOP

        if not ctypes.windll.user32.SetParent(self.hwnd, parent.hwnd):
            raise ctypes.WinError()

    @property
    def rect(self):
        """Window Rectangle."""
        r = RECT(0, 0, 0, 0)
        p = byref(r)
        if not ctypes.windll.user32.GetWindowRect(self.hwnd, p):
            raise ctypes.WinError()
        return Rect(
            r.left, r.top, r.right, r.bottom, r.right - r.left, r.bottom - r.top
        )

    @property
    def text(self):
        """Text or Title of the Window."""
        text = (c_wchar * 1024)()
        ctypes.windll.user32.GetWindowTextW(self.hwnd, text, len(text))
        return text.value

    @text.setter
    def text(self, text):
        """Set Text or Title of the Window."""
        if not ctypes.windll.user32.SetWindowTextW(self.hwnd, text):
            raise ctypes.WinError()

    title = text

    @property
    def thread_id(self):
        """ID of the Thread owning the Window."""
        threadid = ctypes.windll.user32.GetWindowThreadProcessId(self.hwnd, 0)
        return threadid

    @property
    def process_id(self):
        """ID of the Process owning the Window."""
        procid = DWORD()
        ctypes.windll.user32.GetWindowThreadProcessId(self.hwnd, byref(procid))
        return procid.value

    @property
    def minimized(self):
        """Is the Window Minimized (IsIconic)."""
        return bool(ctypes.windll.user32.IsIconic(self.hwnd))

    @property
    def visible(self):
        """Visibillity of the Window."""
        return bool(ctypes.windll.user32.IsWindowVisible(self.hwnd))

    @visible.setter
    def visible(self, v):
        """Set Visibillity of the Window."""
        if v:
            self.show()
        else:
            self.hide()

    @property
    def next_sibling(self):
        """Get the next Sibling Window under the same parent."""
        w = self._GetWindow("NEXT")
        if not w:
            raise ctypes.WinError()
        return type(self)(w)

    @property
    def previous_sibling(self):
        """Get the previous Sibling Window under the same parent."""
        w = self._GetWindow("PREV")
        if not w:
            raise ctypes.WinError()
        return type(self)(w)

    @property
    def first_child(self):
        """Get the first child Window."""
        w = self._GetWindow("CHILD")
        if not w:
            raise ctypes.WinError()
        return type(self)(w)

    @property
    def children(self):
        """Get All the Child Windows."""
        children = []
        self.enumerate(children.append)
        return children

    # Methods

    _getwindow_command = dict(
        CHILD=5,
        ENABLEDPOPUP=6,
        FIRST=0,
        LAST=1,
        NEXT=2,
        PREV=3,
        OWNER=4,
    )

    def _GetWindow(self, cmd):
        """ Get a relative Window."""
        cmd = self._getwindow_command.get(cmd, cmd)
        return ctypes.windll.user32.GetWindow(self.hwnd, cmd)

    def stay_on_top(self, b):
        """Set the Stay On Top Flag."""
        if b:
            self.set_pos(after="TOPMOST")
        else:
            self.set_pos(after="NOTOPMOST")

    def to_front(self):
        """Set the as the Foreground Window."""
        if self.minimized:
            self.restore()
        return ctypes.windll.user32.SetForegroundWindow(self.hwnd)

    def bring_to_top(self):
        """Bring the Window and its parents to the top of the Z order."""
        if not ctypes.windll.user32.BringWindowToTop(self.hwnd):
            raise ctypes.WinError()

    _setwindowpos_after = dict(BOTTOM=1, TOP=0, TOPMOST=-1, NOTOPMOST=-2)
    _setwindowpos_flags = dict(SHOW=0x40, HIDE=0x80, NOACTIVATE=0x10)

    def set_pos(
        self,
        *,
        after=...,
        left=...,
        top=...,
        width=...,
        height=...,
        flags=0,
    ):
        """Set position and Placement Flags using SetWindowPos."""
        after = self._setwindowpos_after.get(after, after)
        flags = self._setwindowpos_flags.get(flags, flags)

        if left is ... or top is ...:
            flags |= 2  # NO MOVE
            left = 0
            top = 0

        if width is ... or height is ...:
            flags |= 1  # NO SIZE
            width = 0
            height = 0

        if after is ...:
            flags |= 4  # NO ORDER
            after = 0

        if not ctypes.windll.user32.SetWindowPos(
            self.hwnd, after, left, top, width, height, flags
        ):
            ctypes.WinError()

    _show_window_command = dict(
        FORCEMINIMIZE=11,
        HIDE=0,
        MAXIMIZE=3,
        MINIMIZE=6,
        RESTORE=9,
        SHOW=5,
        SHOWDEFAULT=10,
        SHOWMAXIMIZED=3,
        SHOWMINIMIZED=2,
        SHOWMINNOACTIVE=7,
        SHOWNA=8,
        SHOWNOACTIVATE=4,
        SHOWNORMAL=1,
    )

    def _ShowWindow(self, cmd):
        """Change how the Window is shown."""
        cmd = self._show_window_command.get(cmd, cmd)
        ctypes.windll.user32.ShowWindow(self.hwnd, cmd)

    def show(self):
        self._ShowWindow("SHOW")

    def hide(self):
        self._ShowWindow("HIDE")

    def maximize(self):
        self._ShowWindow("MAXIMIZE")

    def minimize(self):
        self._ShowWindow("MINIMIZE")

    def restore(self):
        self._ShowWindow("RESTORE")

    def enumerate(self, cb):
        """Execute cb on every Child Window.

        the child window is passed to the callback.
        if the callback returns None, enumeration continues.
        If the callback returns a Value, enumeration stops and the value is returned by `enumerate`.
        """
        exc = None
        result = None

        @ctypes.WINFUNCTYPE(BOOL, HWND, LPARAM)
        def _cb(handle, lparam):
            nonlocal result
            try:
                w = type(self)(handle)
                result = cb(w)
                return result is None
            except Exception as e:
                nonlocal exc
                exc = e
                return False

        r = ctypes.windll.user32.EnumChildWindows(self.hwnd, _cb, 0)

        if result is not None:
            return result

        if exc:
            raise exc

        if not r:  # EnumChildWindows returned an error although all _cb returned True
            raise ctypes.WinError()

    def find(self, spec=..., *, after=None, class_name=None, title=None):
        """Find a Child Window using FindWindowEx, by class_name and/or title.

        use on Window.TOP to find a Top-level Window"""
        if after is None:
            after = self.NULL

        if spec is ...:
            w = ctypes.windll.user32.FindWindowExW(
                self.hwnd, after.hwnd, class_name, title
            )
            if not w:
                raise KeyError(
                    "No Window with title and class", self, class_name, title
                )
        else:
            if class_name or title:
                raise TypeError("spec and tile or class_name passed")

            w = ctypes.windll.user32.FindWindowExW(self.hwnd, after.hwnd, spec, None)
            if not w:
                w = ctypes.windll.user32.FindWindowExW(
                    self.hwnd, after.hwnd, None, spec
                )
            if not w:
                raise KeyError("No Window with title or class", self, spec)
        return type(self)(w)

    def search_by_title(self, regex):
        """Return the first child Window with a Title that matches the Regular Expression."""
        regex = re.compile(regex)

        def cb(w):
            if regex.search(w.title):
                return w
            return None

        return self.enumerate(cb)

    # Magic

    def __bool__(self):
        """Is this a real window?"""
        return bool(ctypes.windll.user32.IsWindow(self.hwnd))

    def __eq__(self, other):
        if isinstance(other, Window):
            return self.hwnd == other.hwnd
        return False

    def __hash__(self):
        return hash(self.hwnd)

    def __int__(self):
        return self.hwnd

    def __repr__(self):
        if self:
            return "Window(hwnd={self:#X}, class_name={self.class_name!r}, text={self.title!r})".format(
                self=self
            )
        return "Window(hwnd={self.hwnd:#X}, INVALID)".format(self=self)

    def __format__(self, spec):
        return format(self.hwnd, spec)


Window.DESKTOP = Window.get_desktop_window()
Window.NULL = Window(0)
Window.TOP = Window.NULL
