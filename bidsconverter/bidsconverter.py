from __future__ import absolute_import, division, print_function
import os
import os.path as op
import numpy as np
import argparse


__all__ = ['main', 'convert2bids']


def main():
    """ Calls the convert2bids function with cmd line arguments. """

    DESC = ("This is a command line tool to convert "
            "unstructured data-directories to a BIDS-compatible format")

    parser = argparse.ArgumentParser(description=DESC)

    parser.add_argument('-d', '--directory',
                        help='Directory to be converted.',
                        required=False,
                        default=os.getcwd())

    parser.add_argument('-c', '--config_file',
                        help='Config-file with img. acq. parameters',
                        required=False,
                        default=op.join(os.getcwd(), 'config.json'))

    parser.add_argument('-v', '--validate',
                        help='Run bids-validator',
                        required=False, action='store_true',
                        default=False)

    args = parser.parse_args()
    convert2bids(cfg=args.config_file, directory=args.directory,
                 validate=args.validate)


def convert2bids(cfg, directory, validate):
    """ Converts (raw) MRI datasets to the BIDS-format.

    Parameters
    ----------
    cfg : str
        Path to config-file (either json or YAML file)
    directory : str
        Path to directory with raw data
    validate : bool
        Whether to run bids-validator on the bids-converted data

    Returns
    -------
    layout : BIDSLayout object
        A BIDSLayout object from the pybids package.

    References
    ----------
    .. [1] Gorgolewski, K. J., Auer, T., Calhoun, V. D., Craddock, R. C.,
           Das, S., Duff, E. P., ... & Handwerker, D. A. (2016). The brain
           imaging data structure, a format for organizing and describing
           outputs of neuroimaging experiments. Scientific Data, 3, 160044.
    """
    pass
