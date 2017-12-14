from __future__ import print_function

import json
import os
import os.path as op
import shutil
import fnmatch
import gzip
import nibabel as nib
import numpy as np
import warnings
import subprocess
from collections import OrderedDict
from copy import copy, deepcopy
from glob import glob
from joblib import Parallel, delayed
from .raw2nifti import parrec2nii
from .behav2tsv import Pres2tsv
from .physio import convert_phy
from .utils import check_executable, append_to_json

__version__ = '0.1'


class BIDSConstructor(object):
    """
    Object to convert datasets to BIDS format.

    Attributes
    ----------
    project_dir : str
        Path to project directory
    cfg_file : str
        Path to config-file.

    Methods
    -------
    convert2bids()
        Initialize renaming and conversion project to BIDS-format.
    """

    def __init__(self, project_dir, cfg_file):
        """ Initializes a BIDSConstructor object.

        Parameters
        ----------
        project_dir : str
            Path to project directory
        cfg_file : str
            Path to config-file.
        """

        self.project_dir = project_dir
        self.cfg = None
        self._cfg_file = cfg_file
        self._parrec2nii = check_executable('parrec2nii')
        self._edf2asc = check_executable('edf2asc')
        self._sub_dirs = None
        self._mappings = None
        self._debug = None

        if not check_executable('dcm2niix'):
            msg = ("The program 'dcm2niix' was not found on this computer; "
                   " install from neurodebian repository with "
                   "'apt-get install dcm2niix', otherwise we can't convert "
                   "par/rec (or dicom) to nifti!")
            warnings.warn(msg)

    def convert2bids(self):
        """ Method to call conversion process. """

        self._parse_cfg_file()
        subject_stem = self.cfg['options']['subject_stem']
        self._sub_dirs = sorted(glob(op.join(self.project_dir,
                                             '%s*' % subject_stem)))
        if not self._sub_dirs:
            msg = "Could not find subdirs in %s." % self.project_dir
            raise ValueError(msg)

        for sub_dir in self._sub_dirs:

            sub_name = op.basename(sub_dir)
            print("Processing %s" % sub_name)

            if 'sub-' not in sub_name:
                sub_name = self._extract_sub_nr(sub_name)

            out_dir = self.cfg['options']['out_dir']

            # Important: to find session-dirs, they should be named
            # ses-*something
            sess_dirs = glob(op.join(sub_dir, 'ses-*'))

            if not sess_dirs:
                # If there are no session dirs, use sub_dir
                if self._debug:
                    print("Didn't find any session-dirs; going for subject-dirs")
                cdirs = [sub_dir]
            else:
                cdirs = sess_dirs

            for cdir in cdirs:

                if 'ses-' in op.basename(cdir):
                    this_out_dir = op.join(out_dir, sub_name, op.basename(cdir))
                else:
                    this_out_dir = op.join(out_dir, sub_name)

                overwrite = self.cfg['options']['overwrite']
                already_exists = op.isdir(out_dir)

                if already_exists and not overwrite:
                    print('%s already converted - skipping ...' % this_out_dir)
                    continue

                if self.cfg['options']['mri_type'] == 'dicom':
                    # If dicom-files, then FIRST convert it
                    cmd = ['dcm2niix', '-v', '0', '-b', 'y', '-f',
                           '%n_%p', '%s' % op.join(cdir, 'DICOMDIR')]

                    with open(os.devnull, 'w') as devnull:
                        subprocess.call(cmd, stdout=devnull)

                # First move stuff to bids_converted dir ...
                data_dirs = [self._move_and_rename(cdir, dtype, sub_name)
                             for dtype in self.data_types]

                # ... and then transform/convert everything
                data_dirs = [self._transform(data_dir)
                             for data_dir in data_dirs]

                # ... and extract some extra meta-data
                _ = [self._extract_metadata(data_dir)
                     for data_dir in data_dirs]

                # Check if there are still _epi files in func
                _epi_files = glob(op.join(this_out_dir, 'func', '*_epi.*'))
                fmap_dir = op.join(this_out_dir, 'fmap')
                _ = [shutil.move(f, op.join(fmap_dir, op.basename(f)).replace('task', 'dir'))
                     for f in _epi_files]

    def _parse_cfg_file(self):
        """ Parses config file and sets defaults. """

        self.metadata = {}

        if not op.isfile(self._cfg_file):
            msg = "Couldn't find config-file: %s" % self._cfg_file
            raise IOError(msg)

        with open(self._cfg_file) as config:
            self.cfg = json.load(config, object_pairs_hook=OrderedDict)

        options = self.cfg['options'].keys()
        if 'mri_type' not in options:
            self.cfg['options']['mri_type'] = 'parrec'

        if 'log_type' not in options:
            self.cfg['options']['log_type'] = None

        if 'n_cores' not in options:
            self.cfg['options']['n_cores'] = -1

        if 'subject_stem' not in options:
            self.cfg['options']['subject_stem'] = 'sub'

        if 'out_dir' not in options:
            self.cfg['options']['out_dir'] = op.join(self.project_dir,
                                                     'bids_converted')
        else:
            self.cfg['options']['out_dir'] = op.join(self.project_dir,
                                                     self.cfg['options']['out_dir'])

        if 'overwrite' not in options:
            self.cfg['options']['overwrite'] = False

        if 'spinoza_data' not in options:
            self.cfg['options']['spinoza_data'] = False

        self.metadata['toplevel'] = {'BidsConverterVersion': __version__}
        if 'metadata' in self.cfg.keys():
            self.metadata['toplevel'].update(self.cfg['metadata'])

        DTYPES = ['func', 'anat', 'fmap', 'dwi']
        self.data_types = [c for c in self.cfg.keys() if c in DTYPES]

        if self.cfg['options']['spinoza_data']:
            # If data is from Spinoza centre, set some defaults to ease the process!
            self.metadata['func'] = {'PhaseEncodingDirection': 'j',
                                     'EffectiveEchoSpacing': 0.00034545,
                                     'SliceEncodingDirection': 'k'}

            if 'fmap' in self.cfg.keys():

                if 'epi' in self.cfg['mappings'].keys():
                    # Assume it uses topups
                    self.metadata['fmap'] = {'PhaseEncodingDirection': 'j-'}
                else:
                    # Assume it uses a B0 (1 phasediff, 1 mag)
                    self.metadata['fmap'] = {'EchoTime1': 0.003,
                                             'EchoTime2': 0.008}

        for dtype in self.data_types:

            if 'metadata' in self.cfg[dtype].keys():
                # Set specific dtype metadata
                self.metadata[dtype] = self.cfg[dtype]['metadata']

            for element in self.cfg[dtype].keys():
                # Check if every element has an 'id' field!
                if element == 'metadata':
                    # Skip metadata field
                    continue

                has_id = 'id' in self.cfg[dtype][element]

                if not has_id:
                    msg = ("Element '%s' in data-type '%s' has no field 'id' "
                           "(a unique identifier), which is necessary for "
                           "conversion!" % (element, dtype))
                    raise ValueError(msg)

                if 'metadata' in self.cfg[dtype][element]:
                    self.metadata[dtype][element] = self.cfg[dtype][element]['metadata']

                if dtype == 'func':
                    # Check if func elements have a task field ...
                    has_task = 'task' in self.cfg[dtype][element]
                    if not has_task:
                        # Use (only) key as name as a (hacky) fix ...
                        task_name = self.cfg[dtype][element].keys()[0]
                        print("Setting task-name of element '%s' to '%s'." %
                              (task_name, task_name))
                        self.cfg[dtype][element]['task'] = task_name

        # Set some attributes directly for readability
        self._mappings = self.cfg['mappings']
        self._debug = bool(self.cfg['options']['debug'])
        self._out_dir = self.cfg['options']['out_dir']

        for ftype in ['bold', 'T1w', 'dwi', 'physio', 'events', 'B0',
                      'eyedata', 'epi']:
            if ftype not in self.cfg['mappings'].keys():
                # Set non-existing mappings to None
                self.cfg['mappings'][ftype] = None

    def _move_and_rename(self, cdir, dtype, sub_name):
        """ Does the actual work of processing/renaming/conversion. """

        if 'sub-' not in sub_name:
            sub_name = self._extract_sub_nr(sub_name)

        # The number of coherent element for a given data-type (e.g. runs in
        # bold-fmri, or different T1 acquisitions for anat) ...
        n_elem = len(self.cfg[dtype])

        if n_elem == 0:
            # If there are for some reason no elements, skip method
            return 0

        unallocated = []
        # Loop over contents of dtype (e.g. func)
        for elem in self.cfg[dtype].keys():

            if elem == 'metadata':
                continue

            # Extract "key-value" pairs (info about element)
            kv_pairs = deepcopy(self.cfg[dtype][elem])

            # Extract identifier (idf) from element
            idf = copy(kv_pairs['id'])
            # But delete the field, because we'll loop over the rest of the
            # fields ...
            del kv_pairs['id']

            # common_name is simply sub-[0-9][0-9][0-9]
            common_name = copy(sub_name)

            # Add session-id pair to name if there are sessions!
            if 'ses-' in op.basename(cdir):
                sess_id = op.basename(cdir).split('ses-')[-1]
                common_name += '_%s-%s' % ('ses', sess_id)

            for key, value in kv_pairs.items():
                # Append key-value pair if it's not an empty string
                common_name += '_%s-%s' % (key, value)

            # Find files corresponding to func/anat/dwi/fieldmap
            files = [f for f in glob(op.join(cdir, '*%s*' % idf))
                     if op.isfile(f)]

            if not files:  # check one level lower
                files = [f for f in glob(op.join(cdir, '*', '*%s*' % idf))
                         if op.isfile(f)]

            if files:
                if 'ses-' in op.basename(cdir):
                    data_dir = self._make_dir(op.join(self._out_dir, sub_name,
                                                      op.basename(cdir),
                                                      dtype))
                else:
                    data_dir = self._make_dir(op.join(self._out_dir, sub_name,
                                                      dtype))
            else:
                # If there are no files, still create data_dir variable,
                # because something needs to be returned
                data_dir = op.join(self._out_dir, sub_name, dtype)

            for f in files:
                # Rename files according to mapping
                types = []
                for ftype, match in self._mappings.items():
                    if match is None:
                        # if there's no mapping given, skip it
                        continue

                    match = '*%s*' % match
                    if fnmatch.fnmatch(op.basename(f), match):
                        types.append(ftype)

                if len(types) > 1:
                    msg = ("Couldn't determine file-type for file '%s' (i.e. "
                           "there is no UNIQUE mapping; "
                           "is one of the following:\n %r" % (f, types))
                    raise ValueError(msg)

                elif len(types) == 1:
                    filetype = types[0]
                else:
                    unallocated.append(f)
                    # No file found; ends up in unallocated (printed later).
                    continue

                # Create full name as common_name + unique filetype +
                # original extension
                exts = f.split('.')[1:]

                # For some weird reason, people seem to use periods in
                # filenames, so remove all unnecessary 'extensions'
                allowed_exts = ['par', 'rec', 'nii', 'gz', 'dcm', 'pickle',
                                'json', 'edf', 'log', 'bz2', 'tar', 'phy',
                                'cPickle', 'pkl', 'jl', 'tsv', 'csv']
                allowed_exts.extend([s.upper() for s in allowed_exts])

                clean_exts = '.'.join([e for e in exts if e in allowed_exts])
                full_name = op.join(data_dir, common_name + '_%s.%s' %
                                    (filetype, clean_exts))

                # _b0 or _B0 may be used as an identifier (which makes sense),
                # but needs to be removed for BIDS-compatibility
                full_name = full_name.replace('_b0', '').replace('_B0', '')

                if self._debug:
                    print("Renaming '%s' as '%s'" % (f, full_name))

                if not op.isfile(full_name):
                    # only do it if it isn't already done
                    shutil.copyfile(f, full_name)

        if unallocated:
            print('Unallocated files for %s:' % sub_name)
            print('\n'.join(unallocated))

        return data_dir

    def _transform(self, data_dir):
        """ Transforms files to appropriate format (nii.gz or tsv). """

        self._mri2nifti(data_dir, n_cores=self.cfg['options']['n_cores'])
        self._log2tsv(data_dir, type=self.cfg['options']['log_type'])

        if self._mappings['eyedata'] is not None:
            self._edf2tsv(data_dir)

        if self._mappings['physio'] is not None:
            self._phys2tsv(data_dir, n_cores=self.cfg['options']['n_cores'])

        return data_dir

    def _extract_metadata(self, data_dir):

        # Usually, directions (e.g. slice-order acq.) is denoted with x/y/z,
        # but BIDs wants it formatted as i/j/k
        dir_mappings = {'x': 'i', 'y': 'j', 'z': 'k',
                        'x-': 'i-', 'y-': 'j-', 'z-': 'k-'}

        dtype = op.basename(data_dir)
        dtype_metadata = self.metadata['toplevel']

        if self.metadata.get(dtype, None) is not None:
            dtype_metadata.update(self.metadata[dtype])

        jsons = glob(op.join(data_dir, '*.json'))
        func_files = glob(op.join(op.dirname(data_dir), 'func', '*_bold.nii.gz'))

        for json_i in jsons:
            this_metadata = copy(dtype_metadata)

            if '_bold' in json_i:
                func_file = json_i.replace('.json', '.nii.gz')
                TR = nib.load(func_file).header['pixdim'][4]
                n_slices = nib.load(func_file).header['dim'][3]
                slice_times = np.linspace(0, TR, n_slices)
                this_metadata['SliceTiming'] = slice_times.tolist()

            elif dtype == 'fmap':
                if 'phasediff' in json_i:
                    this_metadata['IntendedFor'] = ['func/%s' % op.basename(f)
                                                    for f in func_files]
                elif '_epi' in json_i:
                    int_for = op.basename(json_i.replace('_epi.json','_bold.nii.gz'))
                    this_metadata['IntendedFor'] = 'func/%s' % int_for
            append_to_json(json_i, this_metadata)

    def _compress(self, f):

        with open(f, 'rb') as f_in, gzip.open(f + '.gz', 'wb') as f_out:
            shutil.copyfileobj(f_in, f_out)
        os.remove(f)

    def _mri2nifti(self, directory, n_cores=-1):
        """ Converts raw mri to nifti.gz. """

        # If in "debug-mode", set compress to False to save time
        compress = False if self._debug else True

        if self.cfg['options']['mri_type'] == 'parrec':
            # Do par/rec conversion!
            PAR_files = self._glob(directory, ['.PAR', '.par'])
            if PAR_files:
                Parallel(n_jobs=n_cores)(delayed(parrec2nii)(pfile,
                                                             self.cfg,
                                                             compress)
                                         for pfile in PAR_files)

        elif self.cfg['options']['mri_type'] == 'nifti':
            niftis = self._glob(directory, ['.nii', '.nifti', '.ni'])

            if niftis and compress:
                _ = [self._compress(f) for f in niftis]

        elif self.cfg['options']['mri_type'] == 'nifti-gz':
            # Don't have to do anything if it's already nifti.gz!
            pass

        # Check for left-over unconverted niftis
        if compress:

            niftis = self._glob(directory, ['.nii', '.nifti', '.ni'])

            if niftis:
                _ = [self._compress(f) for f in niftis]

    def _log2tsv(self, directory, type='Presentation'):
        """ Converts behavioral logs to event_files. """

        if type is None:
            pass

        elif type == 'Presentation':
            logs = glob(op.join(directory, '*.log'))
            event_dir = op.join(self.project_dir, 'task_info')

            if not op.isdir(event_dir):
                raise IOError("The event_dir '%s' doesnt exist!" % event_dir)

            for log in logs:
                plc = Pres2tsv(in_file=log, event_dir=event_dir)
                plc.parse()
        else:
            warnings.warn("Conversion of logfiles other than type="
                          "'Presentation' is not yet supported.")

    def _edf2tsv(self, directory):

        idf = self.cfg['mappings']['eyedata']
        if idf:
            edfs = glob(op.join(directory, '*%s*' % idf))

            if edfs:
                # Yet to implement!
                pass

    def _phys2tsv(self, directory, n_cores=-1):

        idf = self.cfg['mappings']['physio']
        phys = glob(op.join(directory, '*%s*' % idf))

        if phys:
            Parallel(n_jobs=n_cores)(delayed(convert_phy)(f) for f in phys)

    def _make_dir(self, path):
        """ Creates dir-if-not-exists-already. """
        if not op.isdir(path):
            os.makedirs(path)

        return path

    def _glob(self, path, wildcards):

        files = []

        for w in wildcards:
            files.extend(glob(op.join(path, '*%s' % w)))

        return sorted(files)

    def _extract_sub_nr(self, sub_name):
        sub_stem = self.cfg['options']['subject_stem']
        nr = sub_name.split(sub_stem)[-1]
        nr = nr.replace('-', '').replace('_', '')
        return 'sub-' + nr
