import argparse
import os
import sys
import traceback
import logging
from raidionicsrads.compute import run_rads


def path(string):
    if os.path.exists(string):
        return string
    else:
        sys.exit(f'File not found: {string}')


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('input_single', metavar='input_single', type=path, help='Path to the single input folder')
    parser.add_argument('input_folder', metavar='input_folder', type=path, help='Path to the cohort input folder')
    parser.add_argument('output_folder', metavar='output_folder', type=path, help='Path to the output folder')
    parser.add_argument('--verbose', help="To specify the level of verbose, Default: warning", type=str,
                        choices=['debug', 'info', 'warning', 'error'], default='warning')

    argsin = sys.argv[1:]
    args = parser.parse_args(argsin)
    input_single_fn = args.input_single
    input_cohort_fn = args.input_cohort
    output_fn = args.output_folder

    logging.basicConfig()
    logging.getLogger().setLevel(logging.WARNING)

    if args.verbose == 'debug':
        logging.getLogger().setLevel(logging.DEBUG)
    elif args.verbose == 'info':
        logging.getLogger().setLevel(logging.INFO)
    elif args.verbose == 'error':
        logging.getLogger().setLevel(logging.ERROR)

    try:
        run_rads(config_filename=config_filename)
    except Exception as e:
        logging.error('{}'.format(traceback.format_exc()))


if __name__ == "__main__":
    logging.info("Internal main call.\n")
    main()

