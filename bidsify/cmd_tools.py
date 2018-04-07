import os
import argparse
import shutil
import os.path as op
from .main import bidsify
from .docker import run_from_docker


def run_bidsify_from_cmd():
    """ Calls the bidsify function with cmd line arguments. """

    DESC = ("This is a command line tool to convert "
            "unstructured data-directories to a BIDS-compatible format")

    parser = argparse.ArgumentParser(description=DESC)

    parser.add_argument('-d', '--directory',
                        help='Directory to be converted.',
                        required=False,
                        default=os.getcwd())

    parser.add_argument('-o', '--out',
                        help='Directory for output.',
                        required=False,
                        default=None)

    parser.add_argument('-c', '--config_file',
                        help='Config-file with img. acq. parameters',
                        required=False,
                        default=op.join(os.getcwd(), 'config.yml'))

    parser.add_argument('-v', '--validate',
                        help='Run bids-validator',
                        required=False, action='store_true',
                        default=False)

    parser.add_argument('-D', '--docker',
                        help='Whether to run in a Docker container',
                        required=False, action='store_true',
                        default=False)

    args = parser.parse_args()
    if args.out is None:
        args.out = op.dirname(args.directory)

    if args.docker:
        run_from_docker(cfg_path=args.config_file, in_dir=args.directory,
                        out_dir=args.out, validate=args.validate)
    else:
        bidsify(cfg_path=args.config_file, directory=args.directory,
                validate=args.validate)


def create_template_config():
    """ Creates a template config (yaml) file """

    DESC = ("This is a command line tool to create a "
            "template ('empty') config file.")

    parser = argparse.ArgumentParser(description=DESC)

    parser.add_argument('-o', '--out_dir',
                        help='Output directory to place file in.',
                        required=False,
                        default=os.getcwd())

    out_dir = parser.parse_args().out_dir
    print("Creating empty config file in %s" % out_dir)

    data_dir = op.join(op.dirname(__file__), 'data')
    template_file = op.join(data_dir, 'template_config.yml')
    shutil.copy(template_file, op.join(out_dir, 'config.yml'))
