Screen 2
=================


Map on the Second screen for games that don't use the 2nd screen.

USAGE
-----

Run

    python -m s2 -h


Configuration can be given by multiple toml files, or strings which are valid toml.

The effective Configuration can be dumped with `--dump-config`


    python -m s2 -c "gui.map='map8192x8192'" -c "logging.loggers.hotkey.level='DEBUG'" --dump-config


Works With
----------

Working on GTA IV. If that works, the code will be refactored heavily to support
multiple games.


LICENSING
---------

The python code in this repository is licensed under eupl

The Images are copied from gta4.net and copyright holder is Rockstar.
