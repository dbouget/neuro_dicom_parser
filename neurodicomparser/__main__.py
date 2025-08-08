import argparse
import os
import sys
import traceback
import logging
from neurodicomparser.Utils.ensure_dcm2nii_present import ensure_dcm2nii_present
from neurodicomparser.Utils.ensure_models_present import ensure_models_present
from neurodicomparser.run import run_sectra_cdmedia, run_manual_structure


def path(string):
    if os.path.exists(string):
        return string
    else:
        sys.exit(f'File not found: {string}')


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('-i', '--input_folder', metavar='IN_DIR', type=path,
                        help='Path to the single input folder', default=None)
    parser.add_argument('-c', '--input_category',
                        help='Granularity contained in the input folder', type=str,
                        choices=['cohort_patient', 'single_patient', 'single_timepoint', 'single_image'],
                        default='single_patient')
    parser.add_argument('-s', '--input_structure',
                        help='Convention used for organized the folders and DICOM content on disk', type=str,
                        choices=['sectra_cdmedia', 'manual'], default='sectra_cdmedia')
    parser.add_argument('-o', '--output_folder', metavar='OUT_DIR', type=path,
                        help='Path to the output folder', default=None)
    parser.add_argument('-v', '--verbose', help="To specify the level of verbose, Default: warning",
                        type=str, choices=['debug', 'info', 'warning', 'error'], default='warning')
    parser.add_argument("--override",
        help="To specifically request existing files to be converted again",
        action="store_true",
    )

    argsin = sys.argv[1:]
    args = parser.parse_args(argsin)
    input_folder = args.input_folder
    input_category = args.input_category
    input_structure = args.input_structure
    dest_folder = args.output_folder
    override = args.override

    logging.basicConfig()
    logging.getLogger().setLevel(logging.WARNING)

    if args.verbose == 'debug':
        logging.getLogger().setLevel(logging.DEBUG)
    elif args.verbose == 'info':
        logging.getLogger().setLevel(logging.INFO)
    elif args.verbose == 'error':
        logging.getLogger().setLevel(logging.ERROR)

    if input_folder is None or not os.path.exists(input_folder):
        logging.error('The provided input folder does not exist!')
        sys.exit()
    try:
        ensure_models_present()
        ensure_dcm2nii_present()
    except Exception as e:
        logging.error(f'Downloading the mandatory resources failed with: {e}')

    try:
        if input_structure == "sectra_cdmedia":
            run_sectra_cdmedia(input_folder=input_folder, input_category=input_category, output_folder=dest_folder,
                               override=override)
        elif input_structure == "manual":
            run_manual_structure(input_folder=input_folder, input_category=input_category, output_folder=dest_folder,
                                 override=override)
        else:
            logging.error('usage: the input_structure option (-s) must be selected from [sectra_cdmedia, manual]')
            sys.exit()
    except Exception as e:
        logging.error(f'Process exited with {e}\n\n{traceback.format_exc()}')


if __name__ == "__main__":
    logging.info("Internal main call.\n")
    main()

