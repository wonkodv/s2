import io
import logging

import toml

from .util import merge_recursive_dict

logger = logging.getLogger(__name__)

DEFAULT_CONFIG = {
    "debug": {
        "save_images": {"screenshot": "images/{time}.png", "current_screen_grab": ""},
        "log_config": False,
        "log_args": False,
    },
    "logging": {
        "version": 1,
        "disable_existing_loggers": True,
        "formatters": {
            "long": {
                "format": "%(filename)s:%(lineno)d:%(levelname)s:%(name)s: %(message)s",
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
            "s2.util.get_image": {"level": "WARNING"},
        },
    },
}


def load_configs(files):
    config = DEFAULT_CONFIG

    for file_name in files:
        if isinstance(file_name, str) and "=" in file_name:
            file_name = io.StringIO(file_name)
        d = toml.load(file_name)
        config = merge_recursive_dict(config, d)
    return config
