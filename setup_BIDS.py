from __future__ import print_function

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
        """ Initializes a BIDSConstructor object. """

        self.project_dir = project_dir
        self.cfg_file = cfg_file
        self.sub_dirs = None
        self.cfg = None
        self.mappings = None

    def convert2bids(self):
        """ Method to call conversion process. """

        self._parse_cfg_file()
        self.sub_dirs = glob(op.join(self.project_dir, 'sub*'))

        if not self.sub_dirs:
            msg = "Could not find subdirs in %s. " \
                  "Make sure they're named 'sub-<nr>.'" % self.project_dir
            raise ValueError(msg)

        if self.cfg['options']['backup']:
            self._backup()

        for sub_dir in self.sub_dirs:

            sub_name = op.basename(sub_dir)
            print("Processing %s" % sub_name)

            sess_dirs = glob(op.join(sub_dir, 'ses*'))

            if not sess_dirs:
                # If there are no session dirs, use sub_dir
                sess_dirs = [sub_dir]

            for sess_dir in sess_dirs:

                data_types = [c for c in self.cfg.keys() if c in ['func', 'anat', 'dwi', 'fmap']]
                succ = [self._process_raw(sess_dir, dtype, sub_name) for dtype in data_types]

    def _parse_cfg_file(self):
        """ Parses config file and sets defaults. """

        with open(self.cfg_file) as config:
            self.cfg = json.load(config, object_pairs_hook=OrderedDict)

        # Definition of sensible defaults
        if not "backup" in self.cfg['options']:
            self.cfg['options']['backup'] = 0

        if not "mri_type" in self.cfg['options']:
            self.cfg['options']['mri_type'] = 'parrec'

        if not "n_cores" in self.cfg['options']:
            self.cfg['options']['n_cores'] = -1

        self.mappings = self.cfg['mappings']

        # Maybe define some defaults here?

    def _backup(self):
        """ Backs up raw data into separate dir. """

        dirs = [d for d in glob(op.join(self.project_dir, 'sub-*')) if op.isdir(d)]
        backup_dir = self._make_dir(op.join(op.dirname(self.project_dir), 'backup_raw'))

        for d in dirs:
            if not op.isdir(d):
                shutil.copytree(d, op.join(backup_dir, op.basename(d)))

    def _process_raw(self, sess_dir, dtype, sub_name):
        """ Does the actual work of processing/renaming/conversion. """
        n_elem = len(self.cfg[dtype])

        if n_elem > 0:
            data_dir = self._make_dir(op.join(sess_dir, dtype))
        else:
            return 0

        # Loop over contents of func/anat/dwi/fieldmap
        for elem in self.cfg[dtype].keys():

            # Kinda ugly; needs a more elegant solution
            tmp = deepcopy(self.cfg[dtype][elem])
            idf = tmp['id']
            del tmp['id']

            # common_name is simply sub-xxx
            common_name = copy(sub_name)

            for key, value in tmp.iteritems():

                # Append key-value pair if it's not an empty string
                if value:
                    common_name += '_%s-%s' % (key, value)

            # Find files corresponding to func/anat/dwi/fieldmap
            files = glob(op.join(sess_dir, '*%s*' % idf))

            for f in files:
                # Rename files according to mapping
                ftype = ''.join([k if v in f else '' for k, v in self.mappings.iteritems()])
                full_name = op.join(data_dir, common_name + '_%s%s' % (ftype, op.splitext(f)[-1]))
                os.rename(f, full_name)

        # Convert stuff to bids-compatible formats (e.g. nii.gz, .tsv, etc.)
        self._mri2nifti(data_dir, n_cores=self.cfg['options']['n_cores'])
        self._log2tsv(data_dir, type=self.cfg['options']['log_type'])
        self._edf2tsv(data_dir)

    def _mri2nifti(self, directory, compress=True, n_cores=-1):
        """ Converts raw mri to nifti.gz. """

        if self.cfg['options']['mri_type'] == 'parrec':
            PAR_files = self._glob(directory, ['.PAR', '.par'])

            try:
                Parallel(n_jobs=n_cores)(delayed(parrec2nii)(pfile, compress, 'nibabel') for pfile in PAR_files)
            except KeyError:
                Parallel(n_jobs=n_cores)(delayed(parrec2nii)(pfile, compress, 'dcm2niix') for pfile in PAR_files)

        elif self.cfg['options']['mri_type'] == 'dicom':
            print('Not yet implemented!')
        else:
            print('Not supported!')

    def _log2tsv(self, directory, type='Presentation'):
        """ Converts behavioral logs to event_files. """

        if type == 'Presentation':
            logs = glob(op.join(directory, '*.log'))
            event_dir = op.join(self.project_dir, 'task_info')

            if not op.isdir(event_dir):
                raise OSError("The event_dir '%s' doesnt exist!" % event_dir)

            for log in logs:
                plc = Pres2tsv(in_file=log, event_dir=event_dir)
                plc.parse()
        else:
            print('Log-conversion other than Presentation is not yet implemented')

    def _edf2tsv(self, directory):

        idf = self.cfg['mappings']['eyedata']
        if idf:
            edfs = glob(op.join(directory, '*%s*' % idf))

            if edfs:

                pass

    def _make_dir(self, path):
        """ Creates dir-if-not-exists-already. """
        if not op.isdir(path):
            os.makedirs(path)

        return path

    def _glob(self, path, wildcards):

        files = []

        for w in wildcards:
            files.extend(glob(op.join(path, '*%s*' % w)))

        return files

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


