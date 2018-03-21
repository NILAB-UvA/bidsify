from __future__ import absolute_import, division, print_function
import os
import os.path as op
import argparse
import shutil
import fnmatch
import warnings
import yaml
import logging
import pandas as pd
from copy import copy, deepcopy
from glob import glob
from joblib import Parallel, delayed
from .mri2nifti import convert_mri
from .phys2tsv import convert_phy
from .docker import run_from_docker
from .utils import (check_executable, _make_dir, _append_to_json,
                    _run_cmd)
from .version import __version__


__all__ = ['run_cmd', 'bidsify']

DTYPES = ['func', 'anat', 'fmap', 'dwi']
MTYPE_PER_DTYPE = dict(
    func=['bold'],
    anat=['T1w', 'T2w', 'FLAIR'],
    dwi=['dwi'],
    fmap=['phasediff', 'magnitude', 'epi']
)

MTYPE_ORDERS = dict(

    T1w=dict(sub=0, ses=1, acq=2, ce=3, rec=4, run=5, T1w=6),
    T2w=dict(sub=0, ses=1, acq=2, ce=3, rec=4, run=5, T2w=6),
    FLAIR=dict(sub=0, ses=1, acq=2, ce=3, rec=4, run=5, FLAIR=6),
    bold=dict(sub=0, ses=1, task=2, acq=3, rec=4, run=5, echo=6, bold=7),
    events=dict(sub=0, ses=1, task=2, acq=3, rec=4, run=5, echo=6, events=7),
    physio=dict(sub=0, ses=1, task=2, acq=3, rec=4, run=5, echo=6, recording=7,
                physio=8),
    stim=dict(sub=0, ses=1, task=2, acq=3, rec=4, run=5, echo=6, recording=7,
              stim=8),
    dwi=dict(sub=0, ses=1, acq=2, run=3, dwi=4),
    phasediff=dict(sub=0, ses=1, acq=2, run=3, phasediff=4),
    magnitude=dict(sub=0, ses=1, acq=2, run=3, magnitude=4),
    epi=dict(sub=0, ses=1, acq=2, run=3, dir=5, epi=6)
)

# For some reason, people seem to use periods in filenames, so
# remove all unnecessary 'extensions'
ALLOWED_EXTS = ['par', 'Par', 'rec', 'Rec', 'nii', 'Ni', 'gz',
                'Gz', 'dcm', 'Dcm', 'dicom', 'Dicom', 'dicomdir',
                'Dicomdir', 'pickle', 'json', 'edf', 'log', 'bz2',
                'tar', 'phy', 'cPickle', 'pkl', 'jl', 'tsv', 'csv',
                'txt', 'bval', 'bvec']
ALLOWED_EXTS.extend([s.upper() for s in ALLOWED_EXTS])


def run_cmd():
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


def bidsify(cfg_path, directory, validate):
    """ Converts (raw) MRI datasets to the BIDS-format [1].

    Parameters
    ----------
    cfg_path : str
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

    cfg = _parse_cfg(cfg_path, directory)
    cfg['orig_cfg_path'] = cfg_path

    if cfg['options']['debug']:
        logging.basicConfig(level=logging.DEBUG)

    if not check_executable('dcm2niix'):
        msg = """The program 'dcm2niix' was not found on this computer;
        install dcm2niix from neurodebian (Linux users) or download dcm2niix
        from Github (link) and compile locally (Mac/Windows); bidsify
        needs dcm2niix to convert MRI-files to nifti!. Alternatively, use
        the bidsify Docker image!"""
        warnings.warn(msg)

    if not check_executable('bids-validator') and validate:
        msg = """The program 'bids-validator' was not found on your computer;
        setting the validate option to False"""
        warnings.warn(msg)

    if not check_executable('bids-validator') and validate:
        msg = """The program 'bids-validator' was not found on your computer;
        setting the validate option to False"""
        warnings.warn(msg)
        validate = False

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
    found_sub_dirs = sorted(glob(op.join(cfg['options']['out_dir'], 'sub-*')))
    sub_names = [op.basename(s) for s in found_sub_dirs]

    participants_tsv = pd.DataFrame(index=range(len(sub_names)),
                                    columns=['participant_id'])
    participants_tsv['participant_id'] = sub_names
    f_out = op.join(cfg['options']['out_dir'], 'participants.tsv')
    participants_tsv.to_csv(f_out, sep='\t', index=False)

    if validate:
        bids_validator_log = op.join(op.dirname(cfg['options']['out_dir']),
                                     'bids_validator_log.txt')
        cmd = ['bids-validator', '--ignoreNiftiHeaders',
               cfg['options']['out_dir']]
        rs = _run_cmd(cmd, outfile=bids_validator_log, verbose=True)
        if rs == 0:
            msg = ("bidsify exited without errors and passed the "
                   "bids-validator checks! For the complete bids-validator "
                   "report, see %s." % bids_validator_log)
            print(msg)
        else:
            msg = ("bidsify exited without errors but the bids-validator "
                   "raised one or more errors. Check the complete "
                   "bids-validator report here: %s." % bids_validator_log)
            raise ValueError(msg)


def _process_directory(cdir, out_dir, cfg, is_sess=False):
    """ Main workhorse of bidsify """

    options = cfg['options']

    if is_sess:
        sub_name = _extract_sub_nr(options['subject_stem'],
                                   op.basename(op.dirname(cdir)))
        sess_name = op.basename(cdir)
        this_out_dir = op.join(out_dir, sub_name, sess_name)
        print("... processing session '%s'" % sess_name)
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
    if already_exists:
        print('%s already converted - skipping ...' % this_out_dir)
        return

    # Make dir and copy all files to this dir
    _make_dir(this_out_dir)
    [shutil.copy(f, this_out_dir) for f in glob(op.join(cdir, '*'))]

    # First, convert all MRI-files
    convert_mri(this_out_dir, cfg)
    [os.remove(f) for f in glob(op.join(this_out_dir, '*ADC*.nii.gz'))]

    # If spinoza-data (there is no specific config), try to infer elements
    # from converted data
    if op.basename(cfg['orig_cfg_path']) == 'spinoza_cfg.yml':
        dtype_elements = _infer_dtype_elements(this_out_dir)
        cfg.update(dtype_elements)

    data_types = [c for c in cfg.keys() if c in DTYPES]
    cfg['data_types'] = data_types
    _add_metadata(cfg)

    # Rename and move stuff
    data_dirs = [_move_and_rename(this_out_dir, dtype, sub_name, cfg)
                 for dtype in cfg['data_types']]
    data_dirs = [ddir for ddir in data_dirs if ddir is not None]

    # Also, while we're at it, remove bval/bvecs of topups
    epi_bvals_bvecs = glob(op.join(this_out_dir, 'fmap', '*_epi.bv[e,a][c,l]'))
    [os.remove(f) for f in epi_bvals_bvecs]

    unallocated = [f for f in glob(op.join(this_out_dir, '*')) if op.isfile(f)]
    if unallocated:
        print('Unallocated files for %s:' % sub_name)
        print('\n'.join(unallocated))

        unall_dir = op.join(op.dirname(cfg['options']['out_dir']),
                            'unallocated', sub_name)
        _make_dir(unall_dir)
        for f in unallocated:
            shutil.move(f, unall_dir)

    # 2. Transform PHYS (if any)
    if cfg['mappings']['physio'] is not None:
        idf = cfg['mappings']['physio']
        n_cores = cfg['options']['n_cores']
        phys = sorted(glob(op.join(this_out_dir, '*', '*%s*' % idf)))
        Parallel(n_jobs=n_cores)(delayed(convert_phy)(f) for f in phys)

    # ... and extract some extra meta-data
    [_write_metadata(data_dir, cfg) for data_dir in data_dirs]

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

    if 'mri_ext' not in options:
        cfg['options']['mri_ext'] = 'PAR'

    if 'debug' not in options:
        cfg['options']['debug'] = False

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

    if 'spinoza_data' not in options:
        cfg['options']['spinoza_data'] = False

    if 'deface' not in options:
        cfg['options']['deface'] = False

    if cfg['options']['deface'] and 'FSLDIR' not in os.environ.keys():
        warnings.warn("Cannot deface because FSL is not installed ...")
        cfg['options']['deface'] = False

    if cfg['options']['deface']:
        try:
            import nipype
        except ImportError:
            msg = """To enable defacing, you need to install nipype (pip
                  install nipype) manually! Setting deface to False for now"""
            warnings.warn(msg)
            cfg['options']['deface'] = False

    return cfg


def _infer_dtype_elements(directory):

    dtype_elements = dict()
    for dtype in DTYPES:

        for mtype in MTYPE_PER_DTYPE[dtype]:
            files_found = glob(op.join(directory, '*_%s*' % mtype))
            counter = 1
            for f in files_found:
                info = op.basename(f).split('.')[0].split('_')
                info = [s for s in info if 'sub' not in s]
                info = [s for s in info if len(s.split('-')) > 1]
                info_dict = {s.split('-')[0]: s.split('-')[1] for s in info}
                info_dict['id'] = '_'.join(info)

                if mtype in ['phasediff', 'magnitude']:
                    info_dict['id'] += '*_%s' % mtype

                if dtype_elements.get(dtype, None) is None:
                    # If dtype is not yet a key, add it anyway
                    dtype_elements.update({dtype: {'%s_%i' % (mtype, counter): info_dict}})
                    counter += 1
                else:
                    if info_dict not in dtype_elements[dtype].values():
                        dtype_elements[dtype].update({'%s_%i' % (mtype, counter): info_dict})
                        counter += 1

    return dtype_elements


def _add_metadata(cfg):

    these_dtypes = cfg['data_types']

    # Now, extract and set metadata
    metadata = dict()
    metadata['BidsifyVersion'] = __version__
    if 'metadata' in cfg.keys():
        metadata.update(cfg['metadata'])

    if cfg['options']['spinoza_data']:
        # If data is from Spinoza centre, set some sensible defaults!
        spi_cfg = op.join(op.dirname(__file__), 'data',
                          'spinoza_metadata.yml')
        with open(spi_cfg) as f:
            cfg['spinoza_metadata'] = yaml.load(f)

    # Check config for metadata
    for dtype in these_dtypes:

        if 'metadata' in cfg[dtype].keys():
            # Set specific dtype metadata
            metadata[dtype] = cfg[dtype]['metadata']

        for element in cfg[dtype].keys():

            if 'metadata' in cfg[dtype][element].keys():
                metadata[dtype][element] = cfg[dtype][element]['metadata']

    for mtype in MTYPE_ORDERS.keys():

        if mtype not in cfg['mappings'].keys():
            # Set non-existing mappings to None
            cfg['mappings'][mtype] = None

    cfg['metadata'] = metadata
    return cfg


def _move_and_rename(cdir, dtype, sub_name, cfg):
    """ Does the actual work of processing/renaming/conversion. """

    # Define out-Directory
    dtype_out_dir = op.join(cdir, dtype)  # e.g. sub-01/ses-01/anat

    # The number of coherent elements for a given data-type (e.g. runs in
    # bold-fmri, or different T1 acquisitions for anat) ...
    mappings, options = cfg['mappings'], cfg['options']
    n_elem = len(cfg[dtype])

    if n_elem == 0:
        # If there are for some reason no elements, raise error
        raise ValueError("The category '%s' does not have any entries in your "
                         "config-file!" % dtype)

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
            return None
        else:
            data_dir = _make_dir(dtype_out_dir)

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
            these_keys = these_kv_pairs.keys()
            for key_value in op.basename(f).split('_'):
                if len(key_value.split('-')) == 2:
                    key, value = key_value.split('-')
                    # If allowed (part of BIDS-spec) and not already added ...
                    if key in allowed_keys and key not in these_keys:
                        these_kv_pairs.update({key: value})

            # Sort kv-pairs using MTYPE_ORDERS
            this_order = MTYPE_ORDERS[mtype]
            ordered = sorted(zip(these_kv_pairs.keys(),
                                 these_kv_pairs.values()),
                             key=lambda x: this_order[x[0]])
            kv_string = '_'.join(['-'.join(s) for s in ordered])

            # Create full name as common_name + unique filetype + original ext
            exts = op.basename(f).split('.')[1:]
            clean_exts = '.'.join([e for e in exts if e in ALLOWED_EXTS])

            full_name = kv_string + '_%s.%s' % (mtype, clean_exts)
            full_name = op.join(data_dir, full_name)
            if mtype == 'bold':
                if 'task-' not in op.basename(full_name):
                    msg = ("Could not assign task-name to file %s; please "
                           "put this in the config-file under data-type 'func'"
                           "and element '%s'" % (f, elem))
                    raise ValueError(msg)

            if options['debug']:
                print("Renaming '%s' to '%s'" % (f, full_name))

            if not op.isfile(full_name):
                # only do it if it isn't already done
                shutil.move(f, full_name)

    return data_dir


def _write_metadata(data_dir, cfg):

    # Get metadata dict
    metadata, mappings = cfg['metadata'], cfg['mappings']
    if 'spinoza_metadata' in cfg.keys():
        spi_md = cfg['spinoza_metadata']

    dtype = op.basename(data_dir)

    # Start with common metadata ("toplevel")
    dtype_metadata = copy(metadata)

    # If there is dtype-specific metadata, append it
    if metadata.get(dtype, None) is not None:
        dtype_metadata.update(metadata[dtype])

    if 'ses-' in op.basename(op.dirname(data_dir)):
        ses2append = op.basename(op.dirname(data_dir))
    else:
        ses2append = ''

    # Now loop over ftypes ('filetypes', e.g. bold, physio, etc.)
    for mtype in mappings.keys():

        # Copy common dtype metadata
        mtype_metadata = copy(dtype_metadata)

        # Check if specific ftype metadata exists and, if so, append it
        if dtype in metadata.keys():
            if metadata[dtype].get(mtype, None) is not None:
                mtype_metadata.update(metadata[dtype][mtype])

        if dtype == 'fmap' and mtype == 'phasediff':
            # Find 'bold' files, needed for IntendedFor field of fmaps,
            # assuming a single phasediff file for all bold-files
            func_files = glob(op.join(op.dirname(data_dir),
                                      'func', '*_bold.nii.gz'))

            mtype_metadata['IntendedFor'] = [op.join(ses2append, 'func', op.basename(f))
                                             for f in func_files]

        # Find relevant jsons
        jsons = glob(op.join(data_dir, '*_%s.json' % mtype))

        for this_json in jsons:
            # Loop over jsons
            fbase = op.basename(this_json)
            if 'acq' in fbase:
                acqtype = fbase.split('acq-')[-1].split('_')[0]

            # this_metadata refers to metadata meant for current json
            this_metadata = copy(mtype_metadata)
            if 'spinoza_metadata' in cfg.keys():
                # Append spinoza metadata to current json according to dtype
                # (anat, func, etc.) and mtype (phasediff, bold, etc.)
                if spi_md.get(dtype, None) is not None:
                    tmp_metadata = spi_md.get(dtype)
                    if tmp_metadata.get(mtype, None) is not None:
                        tmp_metadata = tmp_metadata.get(mtype)
                        if tmp_metadata.get(acqtype, None) is not None:
                            tmp_metadata = tmp_metadata.get(acqtype)
                    this_metadata.update(tmp_metadata)

            if mtype == 'epi':

                pardir = op.dirname(op.dirname(this_json))
                dir_idf = fbase.split('dir-')[1].split('_')[0]
                acq_idf = fbase.split('acq-')[1].split('_')[0]

                if dir_idf == 'dwi':
                    cdwi = op.basename(glob(op.join(pardir, 'dwi', '*%s*_dwi.nii.gz' % acq_idf))[0])
                    int_for = op.join(ses2append, 'dwi', cdwi)
                else:  # assume bold
                    cbold = op.basename(glob(op.join(pardir, 'func', '*task-%s*acq-%s*_bold.nii.gz' % (dir_idf, acq_idf)))[0])
                    int_for = op.join(ses2append, 'func', cbold)
                this_metadata['IntendedFor'] = int_for

            if mtype == 'bold':
                task_name = fbase.split('task-')[1].split('_')[0]
                this_metadata.update({'TaskName': task_name})

            _append_to_json(this_json, this_metadata)


def _deface(f):
    """ Deface anat data. """

    _run_cmd(['pydeface', f])  # Run pydeface
    os.rename(f.replace('.nii.gz', '_defaced.nii.gz'), f)  # Revert to old name


def _extract_sub_nr(sub_stem, sub_name):
    nr = sub_name.split(sub_stem)[-1]
    nr = nr.replace('-', '').replace('_', '')
    return 'sub-' + nr