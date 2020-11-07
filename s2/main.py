import argparse
import logging
import logging.config
import pathlib
import toml
import threading
import io

logger = logging.getLogger(__name__)


def get_arg_parser():
    parser = argparse.ArgumentParser(prog=__package__)
    parser.add_argument('--config', '-c',
                        action='append',
                        help="Config files .toml",
                        )
    parser.add_argument('tests',
                        nargs="*",
                        type=pathlib.Path,
                        help="Some Test images to analyze",
                        )

    # TODO: config file.toml

    return parser



def load_configs(files):
    df = []
    for f in files:
        p = pathlib.Path(f)
        if p.is_file:
            df.append(p)
        elif "=" in f:
            df.append(io.StringIO(f)) # TODO: does not work yet

    config = toml.load(df)

    return config


def run(config):
    from . import position_updater
    from . import gui

    g, send_update = gui.create(config)

    pu =  position_updater.create(config, send_update)
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
    config = load_configs(options.config)

    logging.config.dictConfig(config['logging'])
    logger.debug(options)

    try:
        run(config)

    except Exception as e:
        logger.exception("Exception while doing stuff")
        return 1
    return 0
