import getopt
import os
import sys
import logging
import traceback
from neurodicomparser.Utils.ensure_dcm2nii_present import ensure_dcm2nii_present
from neurodicomparser.Utils.ensure_models_present import ensure_models_present
from neurodicomparser.run import run_cohort, run_single

os.environ['TF_CPP_MIN_LOG_LEVEL'] = '3'


def main(argv):
    single_folder = None
    cohort_folder = None
    dest_folder = None
    try:
        logging.basicConfig(format="%(asctime)s ; %(name)s ; %(levelname)s ; %(message)s", datefmt='%d/%m/%Y %H.%M')
        logging.getLogger().setLevel(logging.WARNING)
        opts, args = getopt.getopt(argv, "h:i:f:o:v:", ["input_single=", "input_folder=", "output_folder=", "Verbose="])
    except getopt.GetoptError:
        print('usage: main.py -i <src_single_folder> -f <src_cohort_folder> -o <dest_folder> (--Verbose <mode>)')
        sys.exit(2)
    for opt, arg in opts:
        if opt == '-h':
            print('main.py -i <src_single_folder> -f <src_cohort_folder> -o <dest_folder> (--Verbose <mode>)')
            sys.exit()
        elif opt in ("-i", "--input_single"):
            single_folder = arg
        elif opt in ("-f", "--input_folder"):
            cohort_folder = arg
        elif opt in ("-o", "--output_folder"):
            dest_folder = arg
        elif opt in ("-v", "--Verbose"):
            if arg.lower() == 'debug':
                logging.getLogger().setLevel(logging.DEBUG)
            elif arg.lower() == 'info':
                logging.getLogger().setLevel(logging.INFO)
            elif arg.lower() == 'warning':
                logging.getLogger().setLevel(logging.WARNING)
            elif arg.lower() == 'error':
                logging.getLogger().setLevel(logging.ERROR)

    if single_folder is not None and cohort_folder is not None:
        print('usage: either use -i or -f options, not both!')
        sys.exit()
    try:
        ensure_models_present()
        ensure_dcm2nii_present()
    except Exception as e:
        logging.error(f'Downloading the mandatory resources failed with: {e}')
    try:
        if single_folder is not None:
            run_single(input_folder=single_folder, output_folder=dest_folder)
        else:
            run_cohort(input_folder=cohort_folder, output_folder=dest_folder)
    except Exception as e:
        logging.error('{}'.format(traceback.format_exc()))


if __name__ == "__main__":
    main(sys.argv[1:])
