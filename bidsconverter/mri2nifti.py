from __future__ import print_function, division
import os
import os.path as op
from glob import glob
from .utils import check_executable, _compress, _run_cmd

pigz = check_executable('pigz')


def convert_mri(mri_file, debug, cfg):

    # If already a .nii.gz file, do nothing
    if mri_file[:-6] == '.nii.gz':
        converted_files = listify(mri_file)

    # If in "debug-mode", set compress to False to save time
    compress = False if debug else True
    fname, ext = op.splitext(mri_file)

    # If uncompressed '.nii' file, compress and return
    if ext == '.nii':
        if compress:
            _compress(mri_file)
            converted_files = mri_file + '.gz'
            os.remove(mri_file)
        else:
            converted_files = mri_file

    this_dir = op.dirname(mri_file)

    # Construct general dcm2niix command
    base_cmd = ['dcm2niix', '-b', 'y', '-ba', 'y', '-x', 'y']
    if compress:
        base_cmd.extend(['-z', 'y'] if pigz else ['-z', 'i'])
    else:
        base_cmd.extend(['-z', 'n'])

    # If we've gotten this far, mri_file must be either DICOM or par/rec
    if ext in ['.dcm', '.DICOMDIR', '.DICOM']:
        base_cmd.extend(['-f', '%n_%p', '%s' % mri_file])
        _run_cmd(base_cmd)
        # This is not general enough (only works for DICOMDIR files)
        converted_files = glob(op.join(this_dir, '*.nii.gz'))
        os.remove(mri_file)

    if ext in ['.PAR', '.Par', '.par']:
        rec_file = glob(fname + '.[R,r][E,e][C,c]')[0]
        if not rec_file:
            raise ValueError("Could not find REC file corresponding to %s"
                             % mri_file)
        base_cmd.extend(['-f', op.basename(fname), mri_file])
        _run_cmd(base_cmd)
        converted_files = fname + '.nii.gz'
        if 'phasediff' in converted_files:
            converted_files = _rename_phasediff_files(fname)
        os.remove(mri_file)
        os.remove(rec_file)

    converted_files = listify(converted_files)
    for f in converted_files:
        if not op.isfile(f):
            raise ValueError("Conversion didn't yield the correct name "
                             "for file '%s'; expected '%s'"
                             % (mri_file, f))

    return converted_files


def _rename_phasediff_files(fname):
    """ Renames Philips "B0" files (1 phasediff / 1 magnitude) because dcm2niix
    appends (or sometimes prepends) '_ph' to the filename after conversion.
    """

    base_dir = op.dirname(fname)
    jsons = sorted(glob(op.join(base_dir, '*_ph*.json')))
    [os.rename(src=f, dst=f.replace('_phsub', '').replace('_ph.json', '.json'))
     for f in jsons]

    b0_files = sorted(glob(op.join(base_dir, '*phasediff*.nii.gz')))
    new_files = []
    if len(b0_files) == 2:
        # Assume Philips magnitude img
        for i, f in enumerate(b0_files):
            fnew = f.replace('_phsub', 'sub')
            bases = [s for s in op.basename(fnew).split('.')[0].split('_')]
            base = '_'.join([s for s in bases
                            if s[:3] in ['sub', 'ses', 'run', 'acq']])
            new_name = op.join(op.dirname(f), base.replace('_ph', ''))
            if i == 0:
                fnew = new_name + '_magnitude1.nii.gz'
                os.rename(f, fnew)
                new_files.append(fnew)
            else:
                fnew = new_name + '_phasediff.nii.gz'
                os.rename(f, fnew)
                new_files.append(fnew)
    else:
        print("BidsConverter can only handle 1 phasediff/1 magn B0-scans!")
        # Do nothing if there seem to be no b0-files.
        pass

    return new_files


def listify(obj):
    return [obj] if not isinstance(obj, list) else obj
