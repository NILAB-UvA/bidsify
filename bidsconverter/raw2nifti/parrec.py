from __future__ import print_function, division
import os
import os.path as op
import numpy as np
import subprocess
from glob import glob
from ..utils import check_executable


def parrec2nii(PAR_file, converter, compress=True):
    """ Converts par/rec files to nifti.gz. """

    base_dir = op.dirname(PAR_file)
    base_name = op.join(base_dir, op.splitext(PAR_file)[0])
    ni_name = base_name + '.nii.gz'

    REC_file = '%s.REC' % op.splitext(PAR_file)[0]

    if op.isfile(ni_name):
        _ = [os.remove(f) for f in [REC_file] + [PAR_file]]
        return 0

    cmd = _construct_conversion_cmd(base_name, PAR_file, converter, compress)
    with open(os.devnull, 'w') as devnull:
        subprocess.call(cmd, stdout=devnull)

    _rename_b0_files(base_dir=base_dir)
    _ = [os.remove(f) for f in [REC_file] + [PAR_file]]


def _construct_conversion_cmd(base_name, PAR_file, converter, compress):

    CONVERTERS = ['dcm2niix', 'parrec2nii']
    if converter not in CONVERTERS:
        raise ValueError("Unknown converter (%s) specified; please choose "
                         "from: %r" % (converter, CONVERTERS))

    if converter == 'parrec2nii':
        cmd = ['parrec2nii', PAR_file, '-c', '-o', op.dirname(PAR_file)]
        return cmd

    # Pigs is a fast compression algorithm that can be used by dcm2niix
    pigz = check_executable('pigz')

    if compress:
        if pigz:
            cmd = ['dcm2niix', '-b', 'y', '-z', 'y', '-f', op.basename(base_name), PAR_file]
        else:
            cmd = ['dcm2niix', '-b', 'y', '-z', 'i', '-f', op.basename(base_name), PAR_file]
    else:
        cmd = ['dcm2niix', '-b', 'y', '-f', op.basename(base_name), PAR_file]

    return cmd


def _rename_b0_files(base_dir):
    """ Renames b0-files to phasediff and magnitude imgs.

    IMPORTANT: assumes one phasediff and one magnitude img,
    or optionally >1 magnitudes imgs (but not >1 phasediff img).
    """

    jsons = glob(op.join(base_dir, '_ph*.json'))
    if jsons:
        _ = [os.rename(f, f.replace('_ph', '')) for f in jsons]

    b0_files = sorted(glob(op.join(base_dir, '_ph*.nii.gz')))
    if len(b0_files) > 1:

        for i, b0_file in enumerate(b0_files[:-1]):

            if len(b0_files) > 2:
                new_name = b0_file.replace('_ph', '')[:-9] + '_magnitude%i.nii.gz' % (i + 1)
            else:
                new_name = b0_file.replace('_ph', '')[:-9] + '_magnitude.nii.gz'

            os.rename(b0_file, new_name)

        os.rename(b0_files[-1], b0_files[-1].replace('_ph', '')[:-9] + '_phasediff.nii.gz')

    elif len(b0_files) == 1:
        new_name = b0_files[0].replace('_ph', '')
        os.rename(b0_files[0], new_name)

    else:
        # Do nothing if there seem to be no b0-files.
        pass