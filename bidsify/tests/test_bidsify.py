from __future__ import absolute_import, division, print_function
import pytest
import os.path as op
from shutil import rmtree
from bidsify import bidsify

data_path = op.join(op.dirname(op.dirname(op.abspath(__file__))), 'data')
testdata_path = op.join(data_path, 'test_data')
datasets = [op.join(testdata_path, 'PIOP_1')]#,
            #op.join(testdata_path, 'Upgrade_2017')]


@pytest.mark.parametrize('path_to_data', datasets)
def test_bidsify(path_to_data):
    """ Tests bidsify """
    bids_dir = op.join(path_to_data, 'bids_converted')
    if op.isdir(bids_dir):
        rmtree(bids_dir)

    if 'PIOP_1' in path_to_data:
        cfg = op.join(path_to_data, 'config.yml')

    bidsify(cfg_path=cfg, directory=path_to_data, validate=True)
