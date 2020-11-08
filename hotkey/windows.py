"""Hotkeys on the Windows Plattform."""

import queue
import time
import threading


from ctypes import windll, byref, WinError, py_object, addressof
from ctypes.wintypes import MSG, LPARAM

from .keycodes import KEY_CODES


WM_HOTKEY = 0x312
WM_USER = 0x0400
WM_STOP = WM_USER + 1
WM_NOTIFY = WM_USER + 2

MODIFIERS = {
    "ALT": 1,
    "MENU": 1,
    "CTRL": 2,
    "CONTROL": 2,
    "SHIFT": 4,
    "MOD4": 8,
    "WIN": 8,
}

_next_id = 0
HOTKEYS_BY_ID = {}

HK_WORKER_THREAD = None
HK_WORKER_THREAD_ID = None


def do_in_hk_thread(f):
    def wrapper(*args, **kwargs):
        if HK_WORKER_THREAD is None:
            raise Exception("No Hotkey Worker Thread", threading.current_thread())

        t = threading.current_thread()

        if t == HK_WORKER_THREAD:
            return f(*args, **kwargs)

        e = threading.Event()
        data = (e, f, args, kwargs)
        po = py_object(data)
        lp = LPARAM(addressof(po))
        # hold on to lp in local variable so data stays valid
        if not windll.user32.PostThreadMessageW(HK_WORKER_THREAD_ID, WM_NOTIFY, 0, lp):
            raise WinError()

        if not e.wait(timeout=5):
            raise TypeError("Hotkey Worker not Responding", e)

        if e._exception:
            raise e._exception
        return e._result

    return wrapper


@do_in_hk_thread
def register(hk):
    global _next_id

    _next_id = _next_id + 1
    hk._win_hk_id = _next_id

    mod, vk = hk.code

    if not windll.user32.RegisterHotKey(0, hk._win_hk_id, mod, vk):
        raise WinError()

    HOTKEYS_BY_ID[hk._win_hk_id] = hk


@do_in_hk_thread
def unregister(hk):
    if not windll.user32.UnregisterHotKey(0, hk._win_hk_id):
        raise WinError()
    del HOTKEYS_BY_ID[hk._win_hk_id]


def prepare():
    global HK_WORKER_THREAD, HK_WORKER_THREAD_ID
    HK_WORKER_THREAD = threading.current_thread()
    HK_WORKER_THREAD_ID = windll.kernel32.GetCurrentThreadId()


def loop():
    try:
        msg = MSG()
        lpmsg = byref(msg)

        t = threading.current_thread()
        while windll.user32.GetMessageW(lpmsg, 0, 0, 0):
            if msg.message == WM_HOTKEY:
                hk = HOTKEYS_BY_ID[msg.wParam]
                hk._do_callback()
            elif msg.message == WM_STOP:
                return
            elif msg.message == WM_NOTIFY:
                po = py_object.from_address(msg.lParam)
                data = po.value
                e, f, args, kwargs = data
                try:
                    e._result = f(*args, **kwargs)
                    e._exception = None
                except Exception as ex:
                    e._exception = ex
                e.set()
            else:
                raise AssertionError(msg)

    finally:
        HK_WORKER_THREAD = None
        HK_WORKER_THREAD_ID = None


def start():
    pass


def stop():
    assert HK_WORKER_THREAD
    if not windll.user32.PostThreadMessageW(HK_WORKER_THREAD_ID, WM_STOP, 0, 0):
        raise WinError()


def translate(s):
    """Translate a String like ``Ctrl + A`` into the virtual Key Code and modifiers."""
    parts = s.split("+")
    parts = [s.strip() for s in parts]
    try:
        vk = KEY_CODES[parts[-1]]
    except KeyError:
        vk = parts[-1]
        if vk.startswith("0x"):
            vk = int(vk, 0)
        else:
            raise
    mod = 0
    for m in parts[:-1]:
        mod |= MODIFIERS[m.upper()]

    return (mod, vk)
