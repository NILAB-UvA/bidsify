from __future__ import print_function, division
import os
import os.path as op
import subprocess
from glob import glob
from ..utils import check_executable


def parrec2nii(PAR_file, cfg, compress=True):
    """ Converts par/rec files to nifti.gz. """

    base_dir = op.dirname(PAR_file)
    base_name = op.join(base_dir, op.splitext(PAR_file)[0])
    ni_name = base_name + '.nii.gz'

    REC_file = '%s.REC' % op.splitext(PAR_file)[0]

    if op.isfile(ni_name):
        [os.remove(f) for f in [REC_file] + [PAR_file]]
        return 0

    cmd = _construct_conversion_cmd(base_name, PAR_file, compress)
    with open(os.devnull, 'w') as devnull:
        subprocess.call(cmd, stdout=devnull)

    _rename_b0_files(base_dir=base_dir)
    [os.remove(f) for f in [REC_file] + [PAR_file]]


def _construct_conversion_cmd(base_name, PAR_file, compress):

    # Pigs is a fast compression algorithm that can be used by dcm2niix
    pigz = check_executable('pigz')

    if compress:
        if pigz:
            cmd = ['dcm2niix', '-b', 'y', '-z', 'y', '-f',
                   op.basename(base_name), PAR_file]
        else:
            cmd = ['dcm2niix', '-b', 'y', '-z', 'i', '-f',
                   op.basename(base_name), PAR_file]
    else:
        cmd = ['dcm2niix', '-b', 'y', '-f', op.basename(base_name), PAR_file]

    return cmd


def _rename_b0_files(base_dir):
    """ Renames b0-files to fieldmap and magnitude img - which
    is specific to our Philips Achieva 3T scanner!
    """

    jsons = sorted(glob(op.join(base_dir, '*_ph.json')))
    if len(jsons) > 1:
        raise ValueError("Found more than one B0-json! What went wrong?")
    elif len(jsons) == 0:
        return
    else:
        ph_json = jsons[0]

    ph_json_new = ph_json.replace('_ph.json', '.json')
    ph_json = os.rename(ph_json, ph_json_new)

    b0_files = sorted(glob(op.join(base_dir, '*_ph*.nii.gz')))
    if len(b0_files) == 2:
        # Assume Philips magnitude img
        for i, f in enumerate(b0_files):
            base = '_'.join([s for s in op.basename(f).split('.')[0].split('_')
                             if s[:3] in ['sub', 'ses', 'run', 'acq']])
            new_name = op.join(op.dirname(f), base.replace('_ph', ''))
            if i == 0:
                os.rename(f, new_name + '_magnitude1.nii.gz')
            else:
                os.rename(f, new_name + '_phasediff.nii.gz')
    else:
        print("BidsConverter can only handle 1 phasediff/1 magn B0-scans!")
        # Do nothing if there seem to be no b0-files.
        pass
