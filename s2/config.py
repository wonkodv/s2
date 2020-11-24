import io
import logging

import toml

from .util import merge_recursive_dict

logger = logging.getLogger(__name__)

DEFAULT_CONFIG = {
    "gui": {
        "map": "map2048x2048",
        "colors": {
            "player": "orange",
        },
        "poi_files": [
            "pois.toml",
        ],
    },
    "get_image": {
        "title": "GTAIV",
        "size": (1920, 1080),
    },
    "source": {
        "minimap": {
            "map": "map4096x4096",  # The map to find minimap images in
            "groups": 32,  # round player coordinates to this power of 2 when finding map features
            "box_size": 256,  # size in pixel to find features in
        },
    },
    "debug": {
        "save_images": {
            "screenshot": False,
            "minimap_with_matches": "dump/{time}.png",
        },
        "log_config": False,
        "log_args": False,
        "images": [],  # paths to use instead of screenshots for testing
    },
    "logging": {
        "version": 1,
        "disable_existing_loggers": True,
        "formatters": {
            "long": {
                "format": "%(levelname)s %(asctime)s %(filename)s:%(lineno)d %(name)s: %(message)s",
                "datefmt": "%Y-%m-%d %H:%M:%S",
            },
            "short": {
                "format": "%(levelname)s:%(name)s: %(message)s",
                "datefmt": "%Y-%m-%d %H:%M:%S",
            },
        },
        "handlers": {
            "console": {
                "level": "INFO",
                "formatter": "short",
                "class": "logging.StreamHandler",
            },
            "file": {
                "level": "DEBUG",
                "formatter": "long",
                "class": "logging.FileHandler",
                "filename": "log",
                "mode": "w",
            },
        },
        "root": {"handlers": ["console", "file"], "level": "WARNING"},
        "loggers": {
            "s2": {"level": "DEBUG"},
        },
    },
}

_the_config = DEFAULT_CONFIG


def load_configs(files):
    config = DEFAULT_CONFIG

    global _the_config

    if files:
        for file_name in files:
            if isinstance(file_name, str) and "=" in file_name:
                file_name = io.StringIO(file_name)
            d = toml.load(file_name)
            config = merge_recursive_dict(config, d)
        _the_config = config
    return config  # TODO: do not return Value, use `get_config`


def get_config(*keys):
    val = _the_config
    for k in keys:
        val = val[k]
    return val
