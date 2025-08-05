import argparse
import os
import sys
import traceback
import logging
from neurodicomparser.Utils.ensure_dcm2nii_present import ensure_dcm2nii_present
from neurodicomparser.Utils.ensure_models_present import ensure_models_present
from neurodicomparser.run import run_cohort, run_single


def path(string):
    if os.path.exists(string):
        return string
    else:
        sys.exit(f'File not found: {string}')


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('-s', '--input_single', metavar='IN_DIR', type=path,
                        help='Path to the single input folder', default=None)
    parser.add_argument('-c', '--input_cohort', metavar='IN_DIR', type=path,
                        help='Path to the cohort input folder', default=None)
    parser.add_argument('-o', '--output_folder', metavar='OUT_DIR', type=path,
                        help='Path to the output folder', default=None)
    parser.add_argument('-v', '--verbose', help="To specify the level of verbose, Default: warning", type=str,
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

    if input_single_fn is not None and input_cohort_fn is not None:
        print('usage: either use -s (--input_single) or -c (--input_cohort) options, not both!')
        sys.exit()
    try:
        ensure_models_present()
        ensure_dcm2nii_present()
    except Exception as e:
        logging.error(f'Downloading the mandatory resources failed with: {e}')

    try:
        if input_single_fn is not None:
            run_single(input_folder=input_single_fn, output_folder=output_fn)
        else:
            run_cohort(input_folder=input_cohort_fn, output_folder=output_fn)
    except Exception as e:
        logging.error('{}'.format(traceback.format_exc()))


if __name__ == "__main__":
    logging.info("Internal main call.\n")
    main()

