from __future__ import absolute_import, division, print_function
import os
import os.path as op
import argparse
import shutil
import fnmatch
import warnings
import yaml
import pandas as pd
from copy import copy, deepcopy
from glob import glob
from joblib import Parallel, delayed
from .mri2nifti import convert_mri
from .behav2tsv import Pres2tsv
from .phys2tsv import convert_phy
from .docker import run_from_docker
from .utils import (check_executable, _glob, _make_dir, _append_to_json,
                    _run_cmd)
from .version import __version__

__all__ = ['main', 'convert2bids']

DTYPES = ['func', 'anat', 'fmap', 'dwi']
MTYPE_ORDERS = dict(

    T1w=dict(sub=0, ses=1, acq=2, ce=3, rec=4, run=5, T1w=6),
    bold=dict(sub=0, ses=1, task=2, acq=3, rec=4, run=5, echo=6, bold=7),
    events=dict(sub=0, ses=1, task=2, acq=3, rec=4, run=5, echo=6, events=7),
    physio=dict(sub=0, ses=1, task=2, acq=3, rec=4, run=5, echo=6, recording=7,
                physio=8),
    stim=dict(sub=0, ses=1, task=2, acq=3, rec=4, run=5, echo=6, recording=7,
              stim=8),
    dwi=dict(sub=0, ses=1, acq=2, run=3, dwi=4),
    phasediff=dict(sub=0, ses=1, acq=2, run=3, phasediff=4),
    # Note: task is actually not a key for epi, but we treat it as 'bold'
    epi=dict(sub=0, ses=1, acq=2, run=3, task=4, dir=5, epi=6)
)

# For some reason, people seem to use periods in filenames, so
# remove all unnecessary 'extensions'
ALLOWED_EXTS = ['par', '.Par', 'rec', 'Rec', 'nii', 'Ni', 'gz',
                'Gz', 'dcm', 'Dcm', 'dicom', 'Dicom', 'dicomdir',
                'Dicomdir', 'pickle', 'json', 'edf', 'log', 'bz2',
                'tar', 'phy', 'cPickle', 'pkl', 'jl', 'tsv', 'csv',
                'txt']
ALLOWED_EXTS.extend([s.upper() for s in ALLOWED_EXTS])


def main():
    """ Calls the convert2bids function with cmd line arguments. """

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
                        default=op.join(os.getcwd(), 'config.json'))

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
        run_from_docker(cfg=args.config_file, in_dir=args.directory,
                        out_dir=args.out, validate=args.validate)
    else:
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

    if not check_executable('dcm2niix'):
        msg = """The program 'dcm2niix' was not found on this computer;
        install dcm2niix from neurodebian (Linux users) or download dcm2niix
        from Github (link) and compile locally (Mac/Windows). BidsConverter
        needs dcm2niix to convert MRI-files to nifti!. Alternatively, use
        the BidsConverter Docker image!"""
        print(msg)

    if not check_executable('bids-validator') and validate:
        msg = """The program 'bids-validator' was not found on your computer;
        setting the validate option to False"""
        print(msg)

    if not check_executable('bids-validator') and validate:
        msg = """The program 'bids-validator' was not found on your computer;
        setting the validate option to False"""
        print(msg)
        validate = False

    cfg = _parse_cfg(cfg, directory)

    # Extract some values from cfg for readability
    options = cfg['options']
    out_dir = options['out_dir']
    subject_stem = options['subject_stem']

    # Find subject directories
    sub_dirs = sorted(glob(op.join(directory, '%s*' % subject_stem)))
    if not sub_dirs:
        msg = ("Could not find subject dirs in directory %s with subject stem "
               "'%s'." % (directory, subject_stem))
        raise ValueError(msg)

    # Process directories of each subject
    [_process_directory(sub_dir, out_dir, cfg) for sub_dir in sub_dirs]

    # Write example description_dataset.json to disk
    desc_json = op.join(op.dirname(__file__), 'data',
                        'dataset_description.json')
    dst = op.join(cfg['options']['out_dir'], 'dataset_description.json')
    shutil.copyfile(src=desc_json, dst=dst)

    # Write participants.tsv to disk
    sub_names = [op.basename(s) for s in sub_dirs]
    participants_tsv = pd.DataFrame(index=range(len(sub_names)),
                                    columns=['participant_id'])
    participants_tsv['participant_id'] = sub_names
    f_out = op.join(cfg['options']['out_dir'], 'participants.tsv')
    participants_tsv.to_csv(f_out, sep='\t', index=False)


def _process_directory(cdir, out_dir, cfg, is_sess=False):
    """ Main workhorse of BidsConverter """

    options = cfg['options']
    mappings = cfg['mappings']
    n_cores = options['n_cores']

    if is_sess:
        sub_name = _extract_sub_nr(options['subject_stem'],
                                   op.basename(op.dirname(cdir)))
        sess_name = op.basename(cdir)
        this_out_dir = op.join(out_dir, sub_name, sess_name)
        print("\t... processing session '%s'" % sess_name)
    else:
        sub_name = _extract_sub_nr(options['subject_stem'], op.basename(cdir))
        this_out_dir = op.join(out_dir, sub_name)
        print("Processing sub '%s'" % sub_name)

    # Important: to find session-dirs, they should be named
    # ses-*something*
    sess_dirs = sorted(glob(op.join(cdir, 'ses-*')))

    if sess_dirs:
        # Recursive call to _process_directory
        [_process_directory(sess_dir, out_dir, cfg, is_sess=True)
         for sess_dir in sess_dirs]
        return None

    already_exists = op.isdir(this_out_dir)

    if already_exists and not options['overwrite']:
        print('%s already converted - skipping ...' % this_out_dir)
        return

    # If there are DICOMS, we FIRST need to convert them
    dicom_exts = ['DCM', 'dcm', 'DICOMDIR', 'dicomdir', 'Dicom', 'DICOM']
    dicom_files = sorted(_glob(op.join(this_out_dir, '*'), dicom_exts))

    if dicom_files:
        cmd = ['dcm2niix', '-v', '0', '-b', 'y', '-f',
               '%n_%p', '%s' % op.join(cdir, 'DICOMDIR')]
        _run_cmd(cmd)

    # Rename and move stuff
    data_dirs = [_move_and_rename(cdir, dtype, sub_name, this_out_dir, cfg)
                 for dtype in cfg['data_types']]

    # 1. Transform MRI
    mri_exts = ['.PAR', '.par', '.nii', '.nifti', '.Nifti', '.dcm', '.DICOM',
                '.DCM', '.dicom']
    mri_files = sorted(_glob(op.join(this_out_dir, '*'), mri_exts))

    Parallel(n_jobs=n_cores)(delayed(convert_mri)(f, options['debug'], cfg)
                             for f in mri_files)

    # 2. Transform PHYS (if any)
    if mappings['physio'] is not None:
        idf = mappings['physio']
        phys = sorted(glob(op.join(this_out_dir, '*', '*%s*' % idf)))
        Parallel(n_jobs=n_cores)(delayed(convert_phy)(f) for f in phys)

    # ... and extract some extra meta-data
    [_extract_metadata(data_dir, cfg) for data_dir in data_dirs]

    # Last, move topups to fmap dirs (THIS SHOULD BE A SEPARATE FUNC)
    _fix_topups(this_out_dir)

    # Deface
    if options['deface']:
        anat_files = glob(op.join(this_out_dir, 'anat', '*.nii.gz'))
        [_deface(f) for f in anat_files]


def _parse_cfg(cfg_file, raw_data_dir):
    """ Parses config file and sets defaults. """

    if not op.isfile(cfg_file):
        msg = "Couldn't find config-file: %s" % cfg_file
        raise IOError(msg)

    with open(cfg_file) as config:
        cfg = yaml.load(config)

    options = cfg['options'].keys()

    if 'log_type' not in options:
        cfg['options']['log_type'] = None

    if 'n_cores' not in options:
        cfg['options']['n_cores'] = -1
    else:
        cfg['options']['n_cores'] = int(cfg['options']['n_cores'])

    if 'subject_stem' not in options:
        cfg['options']['subject_stem'] = 'sub'

    if 'out_dir' not in options:
        out_dir = op.join(raw_data_dir, 'bids_converted')
        print("Setting out-dir to %s" % out_dir)
        cfg['options']['out_dir'] = out_dir
    else:
        out_dir = cfg['options']['out_dir']
        cfg['options']['out_dir'] = op.join(raw_data_dir, out_dir)

    if 'overwrite' not in options:
        cfg['options']['overwrite'] = False
    else:
        cfg['options']['overwrite'] = bool(cfg['options']['overwrite'])

    if 'spinoza_data' not in options:
        cfg['options']['spinoza_data'] = False
    else:
        cfg['options']['spinoza_data'] = bool(cfg['options']['spinoza_data'])

    if 'deface' not in options:
        cfg['options']['deface'] = False

    if cfg['options']['deface'] and 'FSLDIR' not in os.environ.keys():
        print("Cannot deface because FSL is not installed ...")
        cfg['options']['deface'] = False

    if cfg['options']['deface']:
        try:
            import nipype
        except ImportError:
            print("To enable defacing, you need to install nipype (pip "
                  "install nipype) manually! Setting deface to False for now")
            cfg['options']['deface'] = False

    # Now, extract and set metadata
    metadata = dict()

    # Always add bidsconverter version
    metadata['toplevel'] = dict(BidsConverterVersion=__version__)

    if 'metadata' in cfg.keys():
        metadata['toplevel'].update(cfg['metadata'])

    if cfg['options']['spinoza_data']:
        # If data is from Spinoza centre, set some sensible defaults!
        spi_cfg = op.join(op.dirname(__file__), 'data',
                          'spinoza_metadata.yml')
        with open(spi_cfg) as f:
            cfg['spinoza_metadata'] = yaml.load(f)

    data_types = [c for c in cfg.keys() if c in DTYPES]
    cfg['data_types'] = data_types

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
                    msg = ("Element '%s' (data-type: %s) does not have a "
                           "'task' element associated with it, which is "
                           "necessary for BIDS-compliance!")
                    raise ValueError(msg)

    for mtype in MTYPE_ORDERS.keys():

        if mtype not in cfg['mappings'].keys():
            # Set non-existing mappings to None
            cfg['mappings'][mtype] = None

    cfg['metadata'] = metadata
    return cfg


def _move_and_rename(cdir, dtype, sub_name, out_dir, cfg):
    ''' Does the actual work of processing/renaming/conversion. '''

    # The number of coherent elements for a given data-type (e.g. runs in
    # bold-fmri, or different T1 acquisitions for anat) ...
    mappings, options = cfg['mappings'], cfg['options']
    n_elem = len(cfg[dtype])

    if n_elem == 0:
        # If there are for some reason no elements, raise error
        raise ValueError("The category '%s' does not have any entries in your "
                         "config-file!" % dtype)

    unallocated = []  # Keep track of 'unallocated' files

    # Loop over contents of dtype (e.g. func)
    for elem in cfg[dtype].keys():

        if elem == 'metadata':
            # Skip metadata
            continue

        # Extract "key-value" pairs (info about element)
        kv_pairs = deepcopy(cfg[dtype][elem])

        # Extract identifier (idf) from element ...
        idf = copy(kv_pairs['id'])
        # ... but delete the field, because we'll loop over the rest of the
        # fields!
        del kv_pairs['id']

        common_kv_pairs = {sub_name.split('-')[0]: sub_name.split('-')[1]}

        # Add session-id pair to name if there are sessions!
        if 'ses-' in op.basename(cdir):
            sess_id = op.basename(cdir).split('ses-')[-1]
            common_kv_pairs.update(dict(ses=sess_id))

        # Find files corresponding to func/anat/dwi/fieldmap
        files = [f for f in glob(op.join(cdir, '*%s*' % idf))
                 if op.isfile(f)]

        if not files:
            print("Could not find files for element %s (dtype %s) with "
                  "identifier '%s'" % (elem, dtype, idf))

        data_dir = _make_dir(op.join(out_dir, dtype))

        for f in files:
            # Rename files according to mapping
            these_kv_pairs = deepcopy(common_kv_pairs)
            types = []
            for mtype, match in mappings.items():
                if match is None:
                    # if there's no mapping given, skip it
                    continue

                # Try to find (unique) modality type (e.g. bold, dwi)
                match = '*%s*' % match
                if fnmatch.fnmatch(op.basename(f), match):
                    types.append(mtype)

            if len(types) > 1:
                msg = ("Couldn't determine modality-type for file '%s' (i.e. "
                       "there is no UNIQUE mapping); "
                       "is one of the following:\n %r" % (f, types))
                raise ValueError(msg)
            elif len(types) == 0:
                unallocated.append(f)
                # No file found; ends up in unallocated (printed later).
                continue
            else:
                mtype = types[0]

            # Check if keys in config are allowed
            allowed_keys = list(MTYPE_ORDERS[mtype].keys())
            for key, value in kv_pairs.items():
                # Append key-value pair if in allowed keys
                if key in allowed_keys:
                    these_kv_pairs.update({key: value})
                else:
                    print("Key '%s' in element '%s' (dtype %s) is not an "
                          "allowed key! Choose from %r" %
                          (key, elem, dtype, allowed_keys))

            # Check if there are any keys in filename already
            for key_value in op.basename(f).split('_'):
                if len(key_value.split('-')) == 2:
                    key, value = key_value.split('-')
                    # If allowed (part of BIDS-spec) and not already added ...
                    if key in allowed_keys and key not in these_kv_pairs.keys():
                        these_kv_pairs.update({key: value})

            # Sort kv-pairs using MTYPE_ORDERS
            this_order = MTYPE_ORDERS[mtype]
            ordered = sorted(zip(these_kv_pairs.keys(), these_kv_pairs.values()),
                             key=lambda x: this_order[x[0]])
            kv_string = '_'.join(['-'.join(s) for s in ordered])

            # Create full name as common_name + unique filetype + original ext
            exts = op.basename(f).split('.')[1:]
            clean_exts = '.'.join([e for e in exts if e in ALLOWED_EXTS])

            full_name = kv_string + '_%s.%s' % (mtype, clean_exts)
            full_name = op.join(data_dir, full_name)

            if options['debug']:
                print("Renaming '%s' to '%s'" % (f, full_name))

            if not op.isfile(full_name):
                # only do it if it isn't already done
                shutil.copyfile(f, full_name)

    if unallocated:
        print('Unallocated files for %s:' % sub_name)
        print('\n'.join(unallocated))

    return data_dir


def _extract_metadata(data_dir, cfg):

    # Get metadata dict
    metadata, mappings = cfg['metadata'], cfg['mappings']

    if 'spinoza_metadata' in cfg.keys():
        spi_md = cfg['spinoza_metadata']

    dtype = op.basename(data_dir)

    # Start with common metadata ("toplevel")
    dtype_metadata = copy(metadata['toplevel'])

    # If there is dtype-specific metadata, append it
    if metadata.get(dtype, None) is not None:
        dtype_metadata.update(metadata[dtype])

    # Now loop over ftypes ('filetypes', e.g. bold, physio, etc.)
    for ftype in mappings.keys():

        # Copy common dtype metadata
        ftype_metadata = copy(dtype_metadata)

        # Check if specific ftype metadata exists and, if so, append it
        if dtype in metadata.keys():
            if metadata[dtype].get(ftype, None) is not None:
                ftype_metadata.update(metadata[dtype][ftype])

        # Find functional files (bold), needed for IntendedFor field of fmaps
        func_files = glob(op.join(op.dirname(data_dir),
                                  'func', '*_bold.nii.gz'))

        if dtype == 'func' and ftype == 'bold':
            # Perhaps SliceTiming?
            pass

        if dtype == 'func' and ftype == 'physio':
            # "SamplingFrequency": 100.0,
            # "StartTime": -22.345,
            # "Columns": ["cardiac", "respiratory", "trigger"]
            pass

        if dtype == 'fmap' and ftype == 'phasediff':
            ftype_metadata['IntendedFor'] = ['func/%s' % op.basename(f)
                                             for f in func_files]

            if 'spinoza_metadata' in cfg.keys():
                ftype_metadata.update(spi_md['fmap']['phasediff'])

        if dtype == 'func' and ftype == 'epi':

            if 'spinoza_metadata' in cfg.keys():
                ftype_metadata.update(spi_md['func']['epi'])

        if dtype == 'dwi' and ftype == 'dwi':

            if 'spinoza_metadata' in cfg.keys():
                ftype_metadata.update(spi_md['dwi']['dwi'])

        if dtype == 'dwi' and ftype == 'epi':

            if 'spinoza_metadata' in cfg.keys():
                ftype_metadata.update(spi_md['dwi']['epi'])

        # Find relevant jsons
        jsons = glob(op.join(data_dir, '*_%s.json' % ftype))

        for this_json in jsons:

            # this_metadata refers to metadata meant for current json
            this_metadata = copy(ftype_metadata)

            if dtype == 'func' and ftype == 'epi':
                int_for = op.basename(this_json.replace('_epi.json',
                                                        '_bold.nii.gz'))
                this_metadata['IntendedFor'] = 'func/%s' % int_for

            if dtype == 'func' and ftype == 'bold':
                base = op.basename(this_json)
                task_name = base.split('task-')[-1].split('_')[0]
                this_metadata.update({'TaskName': task_name})

                # Add spinoza-specific metadata if available
                if 'spinoza_metadata' in cfg.keys():
                    acq_type = base.split('acq-')[-1].split('_')[0]
                    if acq_type not in ['MB', 'epi', 'seq']:
                        acq_type = 'seq'
                    this_metadata.update(spi_md['func']['bold'][acq_type])

            _append_to_json(this_json, this_metadata)


def _fix_topups(out_dir):
    """ Because we treat topups as "bold" files, we need to move them to the
    fmap directory. Also, fix names to comply with BIDS. """
    fmap_dir = op.join(out_dir, 'fmap')

    func_epis = glob(op.join(out_dir, 'func', '*_epi.*'))  # both nii.gz/json
    for f_epi in func_epis:

        base = op.basename(f_epi)
        task = base.split('task-')[-1].split('_')[0]
        elems = base.split('_')
        elems = [e for e in base.split('_') if 'task' not in e]
        if 'run-' in base:
            new_name = elems[:-2] + ['dir-%s' % task] + elems[-2:]
        else:
            new_name = elems[:-1] + ['dir-%s' % task] + elems[-1:]

        new_name = op.join(fmap_dir, '_'.join(new_name))
        shutil.move(f_epi, new_name)

    dwi_epis = glob(op.join(out_dir, 'dwi', '*_epi.*'))
    for d_epi in dwi_epis:

        base = op.basename(d_epi)
        if 'run-' in base:
            new_name = elems[:-2] + ['dir-dwi'] + elems[-2:]
        else:
            new_name = elems[:-1] + ['dir-dwi'] + elems[-1:]
        new_name = op.join(fmap_dir, '_'.join(new_name))
        shutil.move(d_epi, new_name)

    # Check for weird 'ADC' files and remove them
    [os.remove(f) for f in glob(op.join(out_dir, 'dwi', '*ADC.nii.gz'))]

    # Also, while we're at it, remove bval/bvecs of topups
    epi_bvals_bvecs = glob(op.join(out_dir, 'fmap', '*_epi.bv[e,a][c,l]'))
    [os.remove(f) for f in epi_bvals_bvecs]


def _deface(f):
    """ Deface anat data. """

    _run_cmd(['pydeface', f])  # Run pydeface
    os.rename(f.replace('.nii.gz', '_defaced.nii.gz'), f)  # Revert to old name


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


def _extract_sub_nr(sub_stem, sub_name):
    nr = sub_name.split(sub_stem)[-1]
    nr = nr.replace('-', '').replace('_', '')
    return 'sub-' + nr
