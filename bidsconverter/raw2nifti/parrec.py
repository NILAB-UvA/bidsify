from __future__ import print_function, division
import os
import os.path as op
import subprocess
from glob import glob
import nibabel as nib
from ..utils import check_executable, append_to_json


def parrec2nii(PAR_file, converter, is_epi, compress=True):
    """ Converts par/rec files to nifti.gz. """

    try:
        par_header = nib.load(PAR_file).header.general_info
        extract_md = True
    except:
        print("Something wrong with the PAR-file; cannot extract (extra) metadata")
        extract_md = False
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

    if is_epi and extract_md:
        # Philips specific hard-coded stuff
        wfs, epi_factor = par_header['water_fat_shift'], par_header['epi_factor']
        ACCELERATION = 3.0
        eff_echo_spacing = (((1000.0) * wfs)/(434.215 * (epi_factor + 1))) / ACCELERATION
        PHASE_ENCODING_DIRECTION = 'j'
        json_file = op.join(op.dirname(PAR_file), op.basename(PAR_file).split('.')[0] + '.json')
        to_append = {'EffectiveEchoSpacing': eff_echo_spacing,
                     'PhaseEncodingDirection': PHASE_ENCODING_DIRECTION}
        append_to_json(json_file, to_append)

    _rename_b0_files(base_dir=base_dir)
    _ = [os.remove(f) for f in [REC_file] + [PAR_file]]


def _construct_conversion_cmd(base_name, PAR_file, converter, compress):

    CONVERTERS = ['dcm2niix', 'parrec2nii']

    if converter not in CONVERTERS:
        raise ValueError("Unknown converter (%s) specified; please choose "
                         "from: %r" % (converter, CONVERTERS))

    if converter == 'parrec2nii':
        cmd = ['parrec2nii', PAR_file, '-o', op.dirname(PAR_file)]

        if compress:
            cmd.append('-c')

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
    """ Renames b0-files to fieldmap and magnitude img - which
    is specific to our Philips Achieva 3T scanner!
    """

    # ECHO_TIMES = {'EchoTime1': 0.003,
    #              'EchoTime2': 0.008}

    jsons = glob(op.join(base_dir, '_ph*.json'))
    jsonsnew = [f.replace('_ph', '').replace('.json', '_fieldmap.json') for f in jsons]
    _ = [os.rename(f, fnew) for f, fnew in zip(jsons, jsonsnew)]

    b0_files = sorted(glob(op.join(base_dir, '*_ph*.nii.gz')))
    if len(b0_files) == 2:
        # Assume Philips fieldmap
        new_names = [op.join(op.dirname(f), op.basename(f).replace('_ph', '').split('_')[0])
                     for f in b0_files]
        os.rename(b0_files[0], new_names[0] + '_magnitude.nii.gz')
        os.rename(b0_files[1], new_names[1] + '_fieldmap.nii.gz')
    else:
        # Do nothing if there seem to be no b0-files.
        pass
