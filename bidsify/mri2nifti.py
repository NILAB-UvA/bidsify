from __future__ import print_function, division
import os
import warnings
import os.path as op
from glob import glob
from .utils import check_executable, _compress, _run_cmd
from shutil import rmtree


PIGZ = check_executable('pigz')


def convert_mri(directory, cfg):

    compress = not cfg['options']['debug']
    mri_ext = cfg['options']['mri_ext']

    base_cmd = "dcm2niix -ba y"
    if compress:
        base_cmd += " -z y" if PIGZ else " -z i"
    else:
        base_cmd += " -z n"

    if mri_ext in ['PAR', 'dcm']:
        mri_files = glob(op.join(directory, '*.%s' % mri_ext))
        for f in mri_files:

            if '.PAR' in f:
                _fix_header_manually_stopped_scan(f)

            basename, ext = op.splitext(op.basename(f))
            par_cmd = base_cmd + " -f %s %s" % (basename, f)
            # if debug, print dcm2niix output
            _run_cmd(par_cmd.split(' '), verbose=cfg['options']['debug'])
            os.remove(f)
            if mri_ext == 'PAR':
                os.remove(f.replace('.%s' % mri_ext, '.REC'))

    elif mri_ext == 'DICOM':
        # Experimental enh DICOM conversion
        dcm_cmd = base_cmd + " -f %n_%p " + directory
        _run_cmd(dcm_cmd.split(' '))

        if op.isdir(op.join(directory, 'DICOM')):
            rmtree(op.join(directory, 'DICOM'))
        
        if op.isfile(op.join(directory, 'DICOMDIR')):
            os.remove(op.join(directory, 'DICOMDIR'))

        im_files = glob(op.join(directory, 'IM_????'))
        _ = [os.remove(f) for f in im_files]

        ps_files = glob(op.join(directory, 'PS_????'))
        _ = [os.remove(f) for f in ps_files]

        xx_files = glob(op.join(directory, 'XX_????'))
        _ = [os.remove(f) for f in xx_files]
    elif mri_ext == 'nifti':
        pass
    else:
        raise ValueError('Please select either PAR, dcm, DICOM or nifti for mri_ext!')

    niis = glob(op.join(directory, '*.nii'))
    if compress:
        for nii in niis:
            _compress(nii)
            os.remove(nii)

    if 'fmap' in cfg.keys():
        idfs = [elem['id'] for elem in cfg['fmap'].values()]
        _rename_phasediff_files(directory, idf=idfs)


def _rename_phasediff_files(directory, idf='phasediff'):
    """ Renames Philips "B0" files (1 phasediff / 1 magnitude) because dcm2niix
    appends (or sometimes prepends) '_ph' to the filename after conversion.
    """

    if not isinstance(idf, list):
        idf = [idf]

    b0_files = []
    for this_idf in idf:
        b0_files += sorted(glob(op.join(directory, '*%s*' % this_idf)))
    
    for f in b0_files:
        if 'real' in op.basename(f):
            os.rename(f, f.replace('real', 'phasediff')) 
        else: 
            if '.nii.gz' in f:
                os.rename(f, f.replace('.nii.gz', 'magnitude1.nii.gz')) 
            else:
                os.rename(f, f.replace('.', 'magnitude1.'))


def _fix_header_manually_stopped_scan(par):

    with open(par, 'r') as f:
        lines = f.readlines()

    found = False
    for line in lines:
        found = 'Max. number of slices/locations' in line
        if found:
            n_slices = int(line.split(':')[-1].strip().replace('\n', ''))
            break

    if not found:
        raise ValueError("Could not determine number of slices from PAR header (%s)!" % par)

    found = False
    for line_nr_of_dyns, line in enumerate(lines):
        found = 'Max. number of dynamics' in line
        if found:
            n_dyns = int(line.split(':')[-1].strip().replace('\n', ''))
            break

    if int(n_dyns) == 1:
        # Not an fMRI file! skip
        return

    if not found:
        raise ValueError("Could not determine number of slices from PAR header (%s)!" % par)

    found = False
    for idx_start_slices, line in enumerate(lines):
        found = '# === IMAGE INFORMATION =' in line
        if found:
            idx_start_slices += 3
            break

    idx_stop_slices = len(lines) - 2
    slices = lines[idx_start_slices:idx_stop_slices]
    actual_n_dyns = len(slices) / n_slices
    
    if actual_n_dyns != n_dyns:
        print("Found %.3f dyns (%i slices) for file %s, but expected %i dyns (%i slices);"
              " going to try to fix it by removing slices from the PAR header ..." %
              (actual_n_dyns, len(slices), op.basename(par), n_dyns, n_dyns*n_slices))

        lines_to_remove = (len(slices) % n_slices) + 1
        if lines_to_remove != 0:
            for i in range(lines_to_remove):
                lines.pop(idx_stop_slices - i)                

            slices = lines[idx_start_slices:(idx_stop_slices - lines_to_remove)]
            actual_n_dyns = len(slices) / n_slices

        # Replacing expected with actual number of dynamics
        lines[line_nr_of_dyns] = lines[line_nr_of_dyns].replace(str(n_dyns),
                                                                str(actual_n_dyns))

        with open(par, 'w') as f_out:
            [f_out.write(line) for line in lines]

