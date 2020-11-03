from . import hotkey

hotkey.start()
hk1 = hotkey.HotKey("F7", print, "Hans")
hk2 = hotkey.HotKey("F6", hotkey.stop)
hotkey.loop()
