from __future__ import print_function, division
import os
import os.path as op
import subprocess
import shutil
import json
from glob import glob
import nibabel as nib
from fnmatch import fnmatch
from ..utils import check_executable, append_to_json


def parrec2nii(PAR_file, cfg, compress=True):
    """ Converts par/rec files to nifti.gz. """

    effective_echo_spacing = None
    # Extract some info from config
    te_diff = cfg['options']['te_diff']
    acc = cfg['options']['SENSE_factor']
    ees = cfg['options']['effective_echo_spacing']
    is_epi = fnmatch(str(PAR_file), '*_bold*')

    try:
        par_header = nib.load(PAR_file).header.general_info
        extract_md = True
    except:
        print("Something wrong with the PAR-file %s; cannot extract (extra) "
              "metadata, such as EffectiveEchoSpacing. If you want to do "
              "B0-unwarping, set this field in the json manually!"
              % op.basename(PAR_file))
        extract_md = False
        if ees is not None:
            effective_echo_spacing = ees

    base_dir = op.dirname(PAR_file)
    base_name = op.join(base_dir, op.splitext(PAR_file)[0])
    ni_name = base_name + '.nii.gz'

    REC_file = '%s.REC' % op.splitext(PAR_file)[0]

    if op.isfile(ni_name):
        _ = [os.remove(f) for f in [REC_file] + [PAR_file]]
        return 0

    cmd = _construct_conversion_cmd(base_name, PAR_file, compress)
    with open(os.devnull, 'w') as devnull:
        subprocess.call(cmd, stdout=devnull)

    if is_epi and extract_md:
        # Philips specific hard-coded stuff
        wfs, epi_factor = par_header['water_fat_shift'], par_header['epi_factor']
        effective_echo_spacing = (((1000.0) * wfs)/
                                  (434.215 * (epi_factor + 1))) / acc / 1000.0

    if effective_echo_spacing is not None:
        json_file = op.join(op.dirname(PAR_file),
                            op.basename(PAR_file).split('.')[0] + '.json')
        to_append = {'EffectiveEchoSpacing': effective_echo_spacing}
        append_to_json(json_file, to_append)

    _rename_b0_files(base_dir=base_dir, te_diff=te_diff)
    _ = [os.remove(f) for f in [REC_file] + [PAR_file]]


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


def _rename_b0_files(base_dir, te_diff):
    """ Renames b0-files to fieldmap and magnitude img - which
    is specific to our Philips Achieva 3T scanner!
    """

    jsons = glob(op.join(base_dir, '*_ph*.json'))

    if len(jsons) == 1:
        jsonnew = jsons[0].replace('_ph', '')
        jsonnew = jsonnew.replace('.json', '_phasediff.json')
        os.rename(jsons[0], jsonnew)
        with open(jsonnew, 'r') as metadata_file:
            metadata = json.load(metadata_file)
            metadata['EchoTime1'] = metadata.pop('EchoTime')
            metadata['EchoTime2'] = metadata['EchoTime1'] + te_diff
            with open(jsonnew, 'w') as new_metadata_file:
                json.dump(metadata, new_metadata_file, indent=4)

    b0_files = sorted(glob(op.join(base_dir, '*_ph*.nii.gz')))
    if len(b0_files) == 2:
        # Assume Philips magnitude img
        new_names = [op.join(op.dirname(f), op.basename(f).replace('_ph', '').split('_')[0])
                     for f in b0_files]
        os.rename(b0_files[0], new_names[0] + '_magnitude1.nii.gz')
        # Make extra copy of mag-file (magnitude2) because otherwise fmriprep
        # crashes!
        shutil.copyfile(new_names[0] + '_magnitude1.nii.gz',
                        new_names[0] + '_magnitude2.nii.gz')
        os.rename(b0_files[1], new_names[1] + '_phasediff.nii.gz')
    else:
        # Do nothing if there seem to be no b0-files.
        pass
