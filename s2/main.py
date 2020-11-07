from . import s2

import argparse
import logging
import pathlib

logger = logging.getLogger(__name__)


def get_arg_parser():
    parser = argparse.ArgumentParser(prog=__package__)
    parser.add_argument('--log-level', '-l',
                        default="DEBUG",  # TODO: "WARNING",
                        help="Log Level of Console Output",
                        )
    parser.add_argument('--log-file', '-f',
                        type=pathlib.Path,
                        help="Log File",
                        )
    parser.add_argument('--log-file-level', '-L',
                        default="INFO",
                        help="Log File Level",
                        )
    parser.add_argument('--save-images', '-s',
                        help="image dump (~/s2/images/{time}.png)",
                        )
    parser.add_argument('--debug-mode', '-d',
                        help="Show, save, breakpoint",
                        )
    parser.add_argument('tests',
                        nargs="*",
                        type=pathlib.Path,
                        help="Some Test images to analyze",
                        )

    return parser


def setup_logging(options):
    root_logger = logging.getLogger(__package__)
    root_logger.setLevel(logging.DEBUG)

    ch = logging.StreamHandler()
    ch.setLevel(options.log_level)
    ch.setFormatter(logging.Formatter('%(levelname)s:%(name)s: %(message)s'))
    root_logger.addHandler(ch)

    if options.log_file:
        fh = logging.FileHandler(options.log_file)
        fh.setLevel(options.log_file_level)
        fh.setFormatter(logging.Formatter(
            '%(filename)s:%(lineno)d:%(levelname)s:%(name)s: %(message)s'))
        root_logger.addHandler(fh)


def main():
    parser = get_arg_parser()
    options = parser.parse_args()
    setup_logging(options)
    logger.debug(options)
    try:
        if not options.tests:
            s2.S2(options.save_images, debug_mode=options.debug_mode).run()
        else:
            s2.S2(debug_mode=options.debug_mode).test(options.tests)

    except Exception as e:
        logger.exception("Exception while doing stuff")
        return 1
    return 0
