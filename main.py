import getopt
import os
import sys
import logging
import traceback

from neurodicomparser.run import run_parser

os.environ['TF_CPP_MIN_LOG_LEVEL'] = '3'


def main(argv):
    """

    """
    config_file = None

    try:
        logging.basicConfig(format="%(asctime)s ; %(name)s ; %(levelname)s ; %(message)s", datefmt='%d/%m/%Y %H.%M')
        logging.getLogger().setLevel(logging.WARNING)
        opts, args = getopt.getopt(argv, "h:c:v", ["config_file=", "Verbose="])
    except getopt.GetoptError:
        print('usage: main.py -c <config_file> (--Verbose <mode>)')
        sys.exit(2)
    for opt, arg in opts:
        if opt == '-h':
            print('main.py -c <config_file> (--Verbose <mode>)')
            sys.exit()
        elif opt in ("-c", "--config_file"):
            config_file = arg
        elif opt in ("-v", "--Verbose"):
            if arg.lower() == 'debug':
                logging.getLogger().setLevel(logging.DEBUG)
            elif arg.lower() == 'info':
                logging.getLogger().setLevel(logging.INFO)
            elif arg.lower() == 'warning':
                logging.getLogger().setLevel(logging.WARNING)
            elif arg.lower() == 'error':
                logging.getLogger().setLevel(logging.ERROR)
    try:
        run_parser(config_fn=config_file)
    except Exception as e:
        logging.error(f'Process crashed with {e}\n\n{traceback.format_exc()}')


if __name__ == "__main__":
    main(sys.argv[1:])
