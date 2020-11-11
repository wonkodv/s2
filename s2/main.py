import argparse
import logging
import logging.config
import pathlib
import threading

import toml
import pprint

logger = logging.getLogger(__name__)


def get_arg_parser():
    parser = argparse.ArgumentParser(prog=__package__)
    parser.add_argument("--config", "-c", action="append", help="Config files .toml")
    parser.add_argument(
        "tests", nargs="*", type=pathlib.Path, help="Some Test images to analyze"
    )

    return parser


def run(config):
    from . import gui, position_updater

    g, send_update = gui.create(config)

    pu = position_updater.create(config, send_update)
    put = threading.Thread(target=pu.run, daemon=True)
    put.start()
    try:
        g.run()
    finally:
        pass
        pu.stop()
        put.join()


def main():
    parser = get_arg_parser()
    options = parser.parse_args()

    from .config import load_configs

    config = load_configs(options.config)
    logging.config.dictConfig(config["logging"])

    if config['debug']['log_args']:
        logger.debug("Arguments: \n%s", pprint.pformat(options))

    if config['debug']['log_config']:
        logger.debug("Config: \n%s", pprint.pformat(config, indent=4, sort_dicts=True))

    try:
        run(config)
    except Exception as e:
        logger.exception("Exception while doing stuff")
        return 1
    return 0
