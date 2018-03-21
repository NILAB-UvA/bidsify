from __future__ import print_function, division
import os
import os.path as op
from glob import glob
from .utils import check_executable, _compress, _run_cmd

PIGZ = check_executable('pigz')


def convert_mri(directory, cfg):

    compress = not cfg['options']['debug']
    mri_ext = cfg['options']['mri_ext']

    base_cmd = "dcm2niix -ba y -x y"
    if compress:
        base_cmd += " -z y" if PIGZ else " -z i"
    else:
        base_cmd += " -z n"

    mri_files = glob(op.join(directory, '*.%s' % mri_ext))
    for f in mri_files:
        if mri_ext == 'PAR':
            basename, ext = op.splitext(op.basename(f))
            par_cmd = base_cmd + " -f %s %s" % (basename, f)
            # if debug, print dcm2niix output
            _run_cmd(par_cmd.split(' '), verbose=cfg['options']['debug'])
            os.remove(f)
            os.remove(f.replace('.%s' % mri_ext, '.REC'))
        else:
            # Experimental
            dcm_cmd = base_cmd + " -f %n_%p " + directory
            _run_cmd(dcm_cmd.split(' '))

    niis = glob(op.join(directory, '*.nii'))
    if compress:
        for nii in niis:
            _compress(nii)
            os.remove(nii)

    _rename_phasediff_files(directory, idf='B0')


def _rename_phasediff_files(directory, idf='B0'):
    """ Renames Philips "B0" files (1 phasediff / 1 magnitude) because dcm2niix
    appends (or sometimes prepends) '_ph' to the filename after conversion.
    """

    b0_files = glob(op.join(directory, '*%s*' % idf))
    new_files = []
    for f in b0_files:
        new_name = f.replace('_phMag.json', '_phasediff.json')
        new_name = new_name.replace('_phMag_1', '_phasediff')
        new_name = new_name.replace('_phMag_2', '_magnitude')
        os.rename(f, new_name)
        new_files.append(new_name)

    return new_files
