import queue
import threading
import time
import weakref
import logging

from . import windows as impl

logger = logging.getLogger(__name__)


__all__ = (
    "HotKey",
    "EventHotKey",
    "HotKeyError",
    "disable_all_hotkeys",
    "enable_all_hotkeys",
    "get_hotkey",
)

_Lock = threading.Lock()

_Started = False


class HotKeyError(Exception):
    pass


class HotKey:
    """System wide HotKey.

    Before use, the hotkey must be registered.
    It can be unregistered, and then re-registered.

    You need to delete the hotkey (or call its `free` method) before a new
    hotkey with the same key combination can be created. (GC will do that at
    some point, do it yourself to be sure). You have to hold on to the hotkey to
    prevent it from unregistering.

    Use inside a with block to takes care of calling register and free (can
    only be used once)
    """

    HOTKEYS = weakref.WeakValueDictionary()

    def __init__(self, hotkey, callback, *args, **kwargs):
        """Create a hotkey, that will call a callback.

        Calls `callback` with `*args` and `**kwargs` when the hotkey is
        triggered (while it is registered).
        """

        self.hotkey = hotkey
        self.logger = logger.getChild(hotkey)
        self.code = code = impl.translate(hotkey)
        self._callback = callback
        self._args = args
        self._kwargs = kwargs
        self.active = False
        with _Lock:
            if code in self.HOTKEYS:
                raise HotKeyError("Duplicate Hotkey", hotkey)
            self.HOTKEYS[code] = self

    def _do_callback(self):
        self.logger.debug("invoked")
        try:
            self._callback(*self._args, **self._kwargs)
        except Exception as e:
            raise

    def register(self):
        with _Lock:
            if not _Started:
                raise HotkeyError("Not started")
            if self.active:
                raise HotKeyError("Already active")
            impl.register(self)
            self.active = True
            self.logger.info("Registered")

    def unregister(self):
        with _Lock:
            if not _Started:
                raise HotkeyError("Not started")
            if not self.active:
                raise HotKeyError("Already deactivated")
            impl.unregister(self)
            self.active = False
            self.logger.info("Unregistered")

    def free(self):
        try:
            self.unregister()
        except HotKeyError:
            pass
        with _Lock:
            try:
                del self.HOTKEYS[self.code]
            except KeyError:
                pass

    def __enter__(self):
        self.register()
        return self

    def __exit__(self, *args):
        self.free()

    def __del__(self):
        with _Lock:
            assert not self.active, "Impl should hang on to obj while active"

    def __repr__(self):
        return "HotKey({0}, active={1}, callback={2})".format(
            self.hotkey, self.active, self._callback.__qualname__
        )


class EventHotKey(HotKey):
    """A hotkey that acts as a threading Event.

    Wait until Hotkey is pressed, Clear and wait again.

    Can be iterated, in which case it yields the time since the last Hotkey was
    triggered last (multiple events are not queued).

    Example that prints the interval of keypress, until the key is pressed twice quickly:

        with EventHotKey("Ctrl+H") as hk:
            for t in hk:
                if t < 0.25:
                    break
                print(t)
    """

    def __init__(self, hotkey):
        self.evt = threading.Event()
        super().__init__(hotkey, self._trigger)
        self.time = time.monotonic()

    def _trigger(self):
        self.evt.set()

    def wait(self):
        """Wait gor hotkey to be pressed.

        Returns the time since hotkey was created or last wait returned.
        """
        if not self.active:
            raise HotKeyError("Not active")
        self.evt.wait()
        t2 = time.monotonic()
        t = t2 - self.time
        self.time = t2
        return t

    def clear(self):
        self.evt.clear()

    def clear_and_wait(self):
        self.clear()
        return self.wait()

    def __iter__(self):
        while True:
            yield self.clear_and_wait()

    def __repr__(self):
        return "EventHotKey({}, {})".format(
            self.hotkey, "Set" if self.evt.is_set() else "NotSet"
        )

    def __del__(self):
        self.evt.set()  # Should not be needed, but otherwise deadlocks show up :-/


def start():
    logger.info("Starting")
    impl.start()
    threading.Thread(target=loop, daemon=True).start()
    while not _Started:
        time.sleep(0)


def loop():
    global _Started
    impl.prepare()
    _Started = True
    logger.info("Hotkey Processing Started")
    impl.loop()
    logger.info("Hotkey Processing Stopped")
    _Started = False


def stop():
    logger.info("Stopping")
    impl.stop()
    while _Started:
        time.sleep(0)
