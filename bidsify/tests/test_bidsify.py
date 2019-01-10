from __future__ import absolute_import, division, print_function
import os
import pytest
import os.path as op
from shutil import rmtree
from bidsify import bidsify

data_path = op.join(op.dirname(op.dirname(op.abspath(__file__))), 'data')
testdata_path = op.join(data_path, 'test_data')
datasets = [op.join(testdata_path, 'PIOP_1'),
            op.join(testdata_path, 'Upgrade_2017'),
            op.join(testdata_path, 'SharedStates')]


@pytest.mark.parametrize('path_to_data', datasets)
def test_bidsify(path_to_data):
    """ Tests bidsify """

    if not op.isdir(path_to_data):
        # Not all datasets are on travis
        print("Couldn't find dataset %s." % path_to_data)
        return None
    else:
        print("Testing dataset %s ..." % path_to_data)

    bids_dir = op.join(path_to_data, 'bids')
    if op.isdir(bids_dir):
        rmtree(bids_dir)

    unall_dir = op.join(path_to_data, 'unallocated')
    if op.isdir(unall_dir):
        rmtree(unall_dir)

    bids_val_text = op.join(path_to_data, 'bids_validator_log.txt')
    if op.isfile(bids_val_text):
        os.remove(bids_val_text)

    if 'Upgrade' in path_to_data:
        cfg = op.join(data_path, 'spinoza_cfg.yml')
    else:
        cfg = op.join(path_to_data, 'raw', 'config.yml')

    bidsify(cfg_path=cfg, directory=op.join(path_to_data, 'raw'),
            validate=True, out_dir=bids_dir)
    rmtree(bids_dir)
    if op.isdir(unall_dir):
        rmtree(unall_dir)

    os.remove(bids_val_text)
