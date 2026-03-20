import argparse
import os
import sys
import traceback
import logging
from neurodicomparser.run import run_parser


def path(string):
    if os.path.exists(string):
        return string
    else:
        sys.exit(f'File not found: {string}')


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('-c', '--config', metavar='IN_DIR', type=path,
                        help='Path to the configuration file', default=None)
    parser.add_argument('-v', '--verbose', help="To specify the level of verbose, Default: warning",
                        type=str, choices=['debug', 'info', 'warning', 'error'], default='warning')

    argsin = sys.argv[1:]
    args = parser.parse_args(argsin)
    input_config = args.config

    logging.basicConfig()
    logging.getLogger().setLevel(logging.WARNING)

    if args.verbose == 'debug':
        logging.getLogger().setLevel(logging.DEBUG)
    elif args.verbose == 'info':
        logging.getLogger().setLevel(logging.INFO)
    elif args.verbose == 'error':
        logging.getLogger().setLevel(logging.ERROR)

    if input_config is None or not os.path.exists(input_config):
        logging.error('The provided configuration file does not exist!')
        sys.exit()

    try:
        run_parser(config_fn=input_config)
    except Exception as e:
        logging.error(f'Process exited with {e}\n\n{traceback.format_exc()}')


if __name__ == "__main__":
    logging.info("Internal main call.\n")
    main()

