import getopt
import os
import sys
import logging
import traceback
from neurodicomparser.Utils.ensure_dcm2nii_present import ensure_dcm2nii_present
from neurodicomparser.Utils.ensure_models_present import ensure_models_present
from neurodicomparser.run import run_sectra_cdmedia, run_manual_structure

os.environ['TF_CPP_MIN_LOG_LEVEL'] = '3'


def main(argv):
    """

    """
    input_folder = None
    input_structure = None
    input_category = None
    dest_folder = None
    override = False
    try:
        logging.basicConfig(format="%(asctime)s ; %(name)s ; %(levelname)s ; %(message)s", datefmt='%d/%m/%Y %H.%M')
        logging.getLogger().setLevel(logging.WARNING)
        opts, args = getopt.getopt(argv, "h:i:c:s:o:v:x", ["input_folder=", "input_category",
                                                        "input_structure=", "output_folder=", "Verbose=", "override"])
    except getopt.GetoptError:
        print('usage: main.py -i <src_cohort_folder> -c <category> -s <folder_structure> -o <dest_folder> (--Verbose <mode>)')
        sys.exit(2)
    for opt, arg in opts:
        if opt == '-h':
            print('main.py -i <src_cohort_folder> -c <category> -s <folder_structure> -o <dest_folder> (--Verbose <mode>)')
            sys.exit()
        elif opt in ("-i", "--input_folder"):
            input_folder = arg
        elif opt in ("-c", "--input_category"):
            input_category = arg
        elif opt in ("-s", "--input_structure"):
            input_structure = arg
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
        elif opt in ("-x", "--override"):
            override = True

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
        logging.error(f'Process crashed with {e}\n\n{traceback.format_exc()}')


if __name__ == "__main__":
    main(sys.argv[1:])
