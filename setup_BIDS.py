from __future__ import print_function

import argparse
import json
import os
import os.path as op
import shutil
import subprocess
import urllib
from collections import OrderedDict
from copy import copy, deepcopy
from glob import glob

from joblib import Parallel, delayed

from raw2nifti import parrec2nii
from behav2tsv import Pres2tsv


class BIDSConstructor(object):

    def __init__(self, project_dir, cfg_file):

        self.project_dir = project_dir
        self.cfg_file = cfg_file
        self.sub_dirs = None
        self.cfg = None
        self.backup = None
        self.mappings = None

    def convert2bids(self, n_cores=-1):

        self._parse_cfg_file()
        self.sub_dirs = glob(op.join(self.project_dir, 'sub*'))

        if self.backup:
            self._backup()

        if not self.sub_dirs:
            msg = "Could not find subdirs in %s. " \
                  "Make sure they're named 'sub-<nr>.'" % self.project_dir
            raise ValueError(msg)

        for sub_dir in self.sub_dirs:

            sess_dirs = glob(op.join(sub_dir, 'ses*'))
            if not sess_dirs:
                sess_dirs = [sub_dir]

            for sess_dir in sess_dirs:
                sub_name = op.basename(sub_dir)
                print("Processing %s" % sub_name)

                data_types = [c for c in self.cfg.keys() if c in ['func', 'anat', 'dwi', 'fmap']]
                succ = [self._process_raw(sess_dir, dtype, sub_name) for dtype in data_types]

    def _parse_cfg_file(self):

        with open(self.cfg_file) as config:
            self.cfg = json.load(config, object_pairs_hook=OrderedDict)

        self.backup = self.cfg['options']['backup']
        self.mappings = self.cfg['mappings']

        # Maybe define some defaults here?

    def _backup(self):

        dirs = [op.join(self.project_dir, d) for d in os.listdir(self.project_dir)]
        backup_dir = op.join(op.dirname(self.project_dir), 'backup_raw')
        _ = [shutil.copytree(d, op.join(backup_dir, op.basename(d))) for d in dirs]

    def _process_raw(self, sess_dir, dtype, sub_name):

        n_elem = len(self.cfg[dtype])

        if n_elem > 0:
            data_dir = self._make_dir(op.join(sess_dir, dtype))
        else:
            return 0

        for elem in self.cfg[dtype].keys():

            tmp = deepcopy(self.cfg[dtype][elem])
            idf = tmp['id']
            del tmp['id']

            common_name = copy(sub_name)

            for key, value in tmp.iteritems():

                if value:
                    common_name += '_%s-%s' % (key, value)

            files = glob(op.join(sess_dir, '*%s*' % idf))

            for f in files:
                ftype = ''.join([k if v in f else '' for k, v in self.mappings.iteritems()])
                full_name = op.join(data_dir, common_name + '_%s%s' % (ftype, op.splitext(f)[-1]))
                os.rename(f, full_name)

        self._parrec2nii(data_dir)
        self._log2tsv(data_dir, type=self.cfg['options']['log_type'])

    def _parrec2nii(self, directory, compress=True):

        PAR_files = glob(op.join(directory, '*.PAR'))
        Parallel(n_jobs=-1)(delayed(parrec2nii)(pfile, compress) for pfile in PAR_files)

    def _log2tsv(self, directory, type='Presentation'):

        if type == 'Presentation':
            logs = glob(op.join(directory, '*.log'))
            event_dir = op.join(self.project_dir, 'task_info')

            for log in logs:
                plc = Pres2tsv(in_file=log, event_dir=event_dir)
                plc.parse()

    def _make_dir(self, path):

        if not op.isdir(path):
            os.makedirs(path)

        return path

def fetch_example_data(directory=None):

    if directory is None:
        directory = os.getcwd()

    url = "https://db.tt/mJ7P8ZUm"
    out_file = op.join(directory, 'sample_data_bids.zip')

    if op.exists(out_file):
        return 'Already downloaded!'

    msg = """ The file you will download is ~885 MB; do you want to continue?
              (Y / N) """
    resp = raw_input(msg)

    if resp in ['Y', 'y', 'yes', 'Yes']:
        print('Downloading test data ...', end='')

        out_dir = op.dirname(out_file)
        if not op.isdir(out_dir):
            os.makedirs(out_dir)

        if not op.exists(out_file):
            urllib.urlretrieve(url, out_file)

        with open(os.devnull, 'w') as devnull:
            subprocess.call(['unzip', out_file, '-d', out_dir], stdout=devnull)
            subprocess.call(['rm', out_file], stdout=devnull)

            print(' done.')
            print('Data is located at: %s' % op.join(out_dir, 'test_data'))

    elif resp in ['N', 'n', 'no', 'No']:
        print('Aborting download.')
    else:
        print('Invalid answer! Choose Y or N.')

    return out_dir


