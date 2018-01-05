from __future__ import absolute_import, division, print_function
import os
import os.path as op
import numpy as np
import argparse
import json
import shutil
import fnmatch
import gzip
import nibabel as nib
import warnings
import subprocess
from collections import OrderedDict
from copy import copy, deepcopy
from glob import glob
from joblib import Parallel, delayed
from .mri2nifti import parrec2nii
from .behav2tsv import Pres2tsv
from .phys2tsv import convert_phy
from .utils import check_executable, append_to_json
from .version import __version__

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
    """
    if not check_executable('dcm2niix'):
        msg = ("The program 'dcm2niix' was not found on this computer; "
               "install dcm2niix from neurodebian (Linux users) or download "
               "dcm2niix from Github (link) "
               "and compile locally (Mac/Windows). BidsConverter needs "
               "dcm2niix to convert MRI-files to nifti!. Alternatively, use "
               "the BidsConverter Docker image!")
        print(msg)

    if not check_executable('bids-validator') and validate:
        msg = ("The program 'bids-validator' was not found on your computer; "
               "setting the validate option to False")
        print(msg)

     if not check_executable('bids-validator') and validate:
         msg = ("The program 'bids-validator' was not found on your computer; "
                "setting the validate option to False")
         print(msg)

    cfg = _parse_cfg(cfg)

    # Extract some values from cfg for readability
    mappings = cfg['mappings']
    options = cfg['options']
    debug = bool(options['debug'])
    out_dir = options['out_dir']
    subject_stem = options['subject_stem']
    overwrite = options['overwrite']

    # Find subject directories
    sub_dirs = sorted(glob(op.join(project_dir, '%s*' % subject_stem)))
    if not sub_dirs:
        msg = ("Could not find subject dirs in directory %s with subject stem "
               "'%s'." % (project_dir, subject_stem))
        raise ValueError(msg)

    [_process_sub_dir(sub_dir) for sub_dir in sub_dirs]


def _process_sub_dir(sub_dir):
    sub_name = op.basename(sub_dir)
    print("Processing %s" % sub_name)

    if 'sub-' not in sub_name:  # Fix subject name if necessary
        sub_name = _extract_sub_nr(sub_name)

    # Important: to find session-dirs, they should be named
    # ses-*something
    sess_dirs = sorted(glob(op.join(sub_dir, 'ses-*')))

    if not sess_dirs:
        # If there are no session dirs, use sub_dir
        if debug:
            print("Didn't find any session-dirs; going for subject-dirs!")
    else:
        cdirs = sess_dirs

    for cdir in cdirs:

        if 'ses-' in op.basename(cdir):
            this_out_dir = op.join(out_dir, sub_name, op.basename(cdir))
        else:
            this_out_dir = op.join(out_dir, sub_name)

        already_exists = op.isdir(this_out_dir)

        if already_exists and not overwrite:
            print('%s already converted - skipping ...' % this_out_dir)
            continue

        mri_type = options['mri_type']
        if mri_type in ['dicom', 'Dicom', 'DICOM', 'dcm']:
            # If dicom-files, then FIRST convert it
            # This should reuse the cmd from mri2nifti
            cmd = ['dcm2niix', '-v', '0', '-b', 'y', '-f',
                   '%n_%p', '%s' % op.join(cdir, 'DICOMDIR')]

            with open(os.devnull, 'w') as devnull:
                subprocess.call(cmd, stdout=devnull)

        # First move stuff to bids_converted dir ...
        data_dirs = [_move_and_rename(cdir, dtype, sub_name)
                     for dtype in data_types]
        # ... and then transform/convert everything
        data_dirs = [_transform(data_dir) for data_dir in data_dirs]

        # ... and extract some extra meta-data
        [_extract_metadata(data_dir) for data_dir in data_dirs]

        # Last, move topups to fmap dirs (THIS SHOULD BE A SEPARATE FUNC)
        epis = glob(op.join(op.dirname(data_dirs[0]), 'func', '*_epi*'))
        fmap_dir = op.join(op.dirname(data_dirs[0]), 'fmap')
        [shutil.move(f, op.join(fmap_dir, op.basename(f)))
         for f in epis]


def _parse_cfg(cfg_file, raw_data_dir):
    ''' Parses config file and sets defaults. '''

    if not op.isfile(cfg_file):
        msg = "Couldn't find config-file: %s" % cfg_file
        raise IOError(msg)

    with open(cfg_file) as config:
        cfg = json.load(config, object_pairs_hook=OrderedDict)

    options = cfg['options'].keys()
    if 'mri_type' not in options:
        cfg['options']['mri_type'] = 'parrec'

    if 'log_type' not in options:
        cfg['options']['log_type'] = None

    if 'n_cores' not in options:
        cfg['options']['n_cores'] = -1

    if 'subject_stem' not in options:
        cfg['options']['subject_stem'] = 'sub'

    if 'out_dir' not in options:
        cfg['options']['out_dir'] = op.join(raw_data_dir, 'bids_converted')
    else:
        out_dir = cfg['options']['out_dir']
        cfg['options']['out_dir'] = op.join(raw_data_dir, out_dir)

    if 'overwrite' not in options:
        cfg['options']['overwrite'] = False

    if 'spinoza_data' not in options:
        cfg['options']['spinoza_data'] = False

    # Now, extract and set metadata
    metadata = dict()

    # Always add bidsconverter version
    metadata['toplevel'] = dict(BidsConverterVersion=__version__)

    if 'metadata' in cfg.keys():
        metadata['toplevel'].update(cfg['metadata'])

    if cfg['options']['spinoza_data']:
        # If data is from Spinoza centre, set some sensible defaults!
        spi_cfg = op.join(op.dirname(__file__), 'data', 'spinoza_metadata.json')
        with open(spi_cfg) as f:
            self.spi_md = json.load(f)

    DTYPES = ['func', 'anat', 'fmap', 'dwi']
    data_types = [c for c in cfg.keys() if c in DTYPES]

    for dtype in data_types:

        if 'metadata' in cfg[dtype].keys():
            # Set specific dtype metadata
            metadata[dtype] = cfg[dtype]['metadata']

        for element in cfg[dtype].keys():
            # Check if every element has an 'id' field!
            if element == 'metadata':
                # Skip metadata field
                continue

            has_id = 'id' in cfg[dtype][element]

            if not has_id:
                msg = ("Element '%s' in data-type '%s' has no field 'id' "
                       "(a unique identifier), which is necessary for "
                       "conversion!" % (element, dtype))
                raise ValueError(msg)

            if 'metadata' in cfg[dtype][element]:
                mdata = cfg[dtype][element]['metadata']
                metadata[dtype][element] = mdata

            if dtype == 'func':
                # Check if func elements have a task field ...
                has_task = 'task' in cfg[dtype][element]

                if not has_task:
                    # Use (only) key as name as a (hacky) fix ...
                    task_name = cfg[dtype][element].keys()[0]
                    print("Setting task-name of element '%s' to '%s'." %
                          (task_name, task_name))
                    cfg[dtype][element]['task'] = task_name

    for ftype in ['bold', 'T1w', 'dwi', 'physio', 'events', 'B0',
                  'eyedata', 'epi']:

        if ftype not in cfg['mappings'].keys():
            # Set non-existing mappings to None
            cfg['mappings'][ftype] = None

    return cfg


def _move_and_rename(self, cdir, dtype, sub_name):
    ''' Does the actual work of processing/renaming/conversion. '''

    if 'sub-' not in sub_name:
        sub_name = self._extract_sub_nr(sub_name)

    # The number of coherent elements for a given data-type (e.g. runs in
    # bold-fmri, or different T1 acquisitions for anat) ...
    n_elem = len(self.cfg[dtype])

    if n_elem == 0:
        # If there are for some reason no elements, skip method
        return None

    unallocated = []
    # Loop over contents of dtype (e.g. func)
    for elem in self.cfg[dtype].keys():

        if elem == 'metadata':
            # Skip metadata
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
        else:
            sess_id = None

        for key, value in kv_pairs.items():
            # Append key-value pair if it's not an empty string
            common_name += '_%s-%s' % (key, value)

        # Find files corresponding to func/anat/dwi/fieldmap
        files = [f for f in glob(op.join(cdir, '*%s*' % idf))
                 if op.isfile(f)]

        if not files:  # check one level lower
            files = [f for f in glob(op.join(cdir, '*', '*%s*' % idf))
                     if op.isfile(f)]

        if sess_id is not None:
            data_dir = self._make_dir(op.join(self._out_dir, sub_name,
                                              'ses-' + sess_id, dtype))
        else:
            data_dir = self._make_dir(op.join(self._out_dir, sub_name,
                                              dtype))
        if files:
            # If we actually found files, make the directory
            data_dir = self._make_dir(data_dir)

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
                print("Renaming '%s' to '%s'" % (f, full_name))

            if not op.isfile(full_name):
                # only do it if it isn't already done
                shutil.copyfile(f, full_name)

    if unallocated:
        print('Unallocated files for %s:' % sub_name)
        print('\n'.join(unallocated))

    return data_dir

def _transform(self, data_dir):
    ''' Transforms files to appropriate format (nii.gz or tsv). '''

    self._mri2nifti(data_dir, n_cores=self.cfg['options']['n_cores'])

    if self._mappings['events'] is not None:
        self._log2tsv(data_dir, logtype=self.cfg['options']['log_type'])

    if self._mappings['physio'] is not None:
        self._phys2tsv(data_dir, n_cores=self.cfg['options']['n_cores'])

    return data_dir

def _extract_metadata(self, data_dir):

    dtype = op.basename(data_dir)
    dtype_metadata = self._metadata['toplevel']
    if self._metadata.get(dtype, None) is not None:
        dtype_metadata.update(self.metadata[dtype])

    for file_type in self._mappings.keys():
        jsons = glob(op.join(data_dir, '*%s*.json' % file_type))
        ftype_metadata = copy(dtype_metadata)

        if dtype in self._metadata.keys():
            if self._metadata[dtype].get(file_type, None) is not None:
                ftype_metadata.update(self._metadata[dtype][file_type])

        func_files = glob(op.join(op.dirname(data_dir),
                                  'func', '*_bold.nii.gz'))
        if dtype == 'fmap' and file_type == 'phasediff':
            ftype_metadata['IntendedFor'] = ['func/%s' % op.basename(f)
                                             for f in func_files]
        for this_json in jsons:
            # This entire loop is ugly; need to refactor
            this_metadata = copy(ftype_metadata)

            if dtype == 'func' and file_type == 'epi':
                int_for = op.basename(this_json.replace('_epi.json',
                                                        '_bold.nii.gz'))
                this_metadata['IntendedFor'] = 'func/%s' % int_for

                if hasattr(self, 'spi_md'):
                    this_metadata.update(self.spi_md['func']['epi'])

            elif dtype == 'func' and file_type == 'bold':

                if hasattr(self, 'spi_md'):
                    mbnames = ['multiband', 'MB3', 'Multiband']
                    if any([s in this_json for s in mbnames]):
                        this_metadata.update(self.spi_md['func']['bold']['MB'])
                    else:  # assume sequential
                        this_metadata.update(self.spi_md['func']['bold']['sequential'])

            elif dtype == 'fmap' and file_type == 'phasediff':

                if hasattr(self, 'spi_md'):
                    this_metadata.update(self.spi_md['fmap']['phasediff'])

            append_to_json(this_json, this_metadata)


def _mri2nifti(self, directory, n_cores=-1):
    ''' Converts raw mri to nifti.gz. '''

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


def _log2tsv(self, directory, logtype='Presentation'):
    ''' Converts behavioral logs to event_files. '''

    if logtype is None:
        if self._debug:
            print("Log_type is not set, so cannot convert events-file!")
    elif logtype == 'Presentation':
        logs = glob(op.join(directory, '*events*'))
        event_dir = op.join(self.project_dir, 'task_info')

        if not op.isdir(event_dir):
            raise IOError("The event_dir '%s' doesnt exist!" % event_dir)

        for log in logs:
            plc = Pres2tsv(in_file=log, event_dir=event_dir)
            plc.parse()
    else:
        warnings.warn("Conversion of logfiles other than type="
                      "'Presentation' is not (yet) supported.")


def _phys2tsv(self, directory, n_cores=-1):

    idf = self.cfg['mappings']['physio']
    phys = glob(op.join(directory, '*%s*' % idf))

    if phys:
        Parallel(n_jobs=n_cores)(delayed(convert_phy)(f) for f in phys)


def _compress(f):

    with open(f, 'rb') as f_in, gzip.open(f + '.gz', 'wb') as f_out:
        shutil.copyfileobj(f_in, f_out)
    os.remove(f)


def _make_dir(path):
    ''' Creates dir-if-not-exists-already. '''

    if not op.isdir(path):
        os.makedirs(path)

    return path


def _glob(path, wildcards):
    ''' Finds files with different wildcards. '''

    files = []
    for w in wildcards:
        files.extend(glob(op.join(path, '*%s' % w)))

    return sorted(files)


def _extract_sub_nr(sub_stem, sub_name):
    nr = sub_name.split(sub_stem)[-1]
    nr = nr.replace('-', '').replace('_', '')
    return 'sub-' + nr
"""
