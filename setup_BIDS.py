from __future__ import print_function
import json
import shutil
import gzip
import os
import urllib
import argparse
import subprocess
import nibabel as nib
import os.path as op
from glob import glob
from copy import copy, deepcopy
from collections import OrderedDict


class BIDSConstructor(object):

    def __init__(self, project_dir, cfg_file):

        self.project_dir = project_dir
        self.cfg_file = cfg_file
        self.sub_dirs = None
        self.cfg = None
        self.backup = None
        self.mappings = None

    def convert2bids(self):

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

    def _parrec2nii(self, directory, compress=True):

        REC_files = glob(op.join(directory, '*.REC'))
        PAR_files = glob(op.join(directory, '*.PAR'))

        # Create scaninfo from PAR and convert .REC to nifti
        for REC, PAR in zip(REC_files, PAR_files):

            REC_name = REC[:-4]

            if not op.exists(REC_name + '.nii') or not op.exists(REC_name + '.nii.gz'):
                PR_obj = nib.parrec.load(REC)
                nib.nifti1.save(PR_obj, REC_name)
                ni_name = REC_name + '.nii'

                # if compress:
                with open(ni_name, 'rb') as f_in, gzip.open(ni_name + '.gz', 'wb') as f_out:
                    shutil.copyfileobj(f_in, f_out)
            else:
                continue

        _ = [os.remove(f) for f in REC_files + PAR_files + glob(op.join(directory, '*.nii'))]

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


if __name__ == '__main__':

    #fetch_example_data()

    parser = argparse.ArgumentParser(description='This is a command line tool to convert '
                                                 'unstructured data-directories to a BIDS-compatible '
                                                 'format.')
    parser.add_argument('-d', '--directory', help='Directory to be converted.', required=False)
    parser.add_argument('-c', '--config_file', help='Config-file with img. acq. parameters', required=False)

    args = parser.parse_args()

    if args.directory is None:
        args.directory = os.getcwd()

    if args.config_file is None:
        args.config_file = op.join(os.getcwd(), 'config.json')

    bids_constructor = BIDSConstructor(args.directory, args.config_file)
    bids_constructor.convert2bids()

