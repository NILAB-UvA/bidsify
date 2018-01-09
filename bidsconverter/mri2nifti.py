from __future__ import print_function, division
import os
import os.path as op
from glob import glob
from .utils import check_executable, _compress, _run_cmd, _glob

pigz = check_executable('pigz')


def convert_mri(directory, cfg):

    compress = not cfg['options']['debug']

    base_cmd = "dcm2niix -ba -y -x y"
    if compress:
        base_cmd += " -z y" if pigz else " -z i"
    else:
        base_cmd += " -z n"

    # Try converting whatever DICOM there is (they don't have a standard
    # output-name or extension)

    # TODO: ask for DICOM id in options, because otherwise we don't know
    # what we're converting (and they end up in unallocated)
    dcm_cmd = base_cmd + " -f %n_%p " + directory
    _run_cmd(dcm_cmd.split(' '))

    # Now, check for PAR/RECs
    pars = glob(op.join(directory, '*.PAR'))
    for par in pars:
        basename, ext = op.splitext(op.basename(par))
        par_cmd = base_cmd + " -f %s %s" % (basename, par)
        _run_cmd(par_cmd.split(' '))
        os.remove(par)
        os.remove(par.replace('.PAR', '.REC'))

    niis = glob(op.join(directory, '*.nii'))
    if compress:
        for nii in niis:
            _compress(nii)
            os.remove(nii)

    if 'phasediff' in converted_files:
        converted_files = _rename_phasediff_files(fname)

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

    b0_files = sorted(glob(op.join(base_dir, '*phasediff*.nii*')))
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
