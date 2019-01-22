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
            n_slices = line.split(':')[-1].strip().replace('\n', '')
            break

    if not found:
        raise ValueError("Could not determine number of slices from PAR header (%s)!" % par)

    found = False
    for line_nr_of_dyns, line in enumerate(lines):
        found = 'Max. number of dynamics' in line
        if found:
            n_dyns = line.split(':')[-1].strip().replace('\n', '')
            break

    if int(n_dyns) == 1:
        return

    if not found:
        raise ValueError("Could not determine number of slices from PAR header (%s)!" % par)
    
    skip_rows_eof = 2
    last_slice_nr = [char for char in lines[-(1+skip_rows_eof)].split(' ') if char][0]
    if not last_slice_nr == n_slices:
        warnings.warn("Number of slices not equal to expected number; "
                      "Scan probably manually stopped. Attempt to fix it ...")

        lines_to_drop = []
        for i, line in enumerate(lines[::-1][skip_rows_eof:]):
            slc = [char for char in line.split(' ') if char][0]
            if slc != n_slices:
                #print("Dropping %s" % (line))
                lines_to_drop.append(line)
            else:
               break

        for to_drop in lines_to_drop:
            lines.pop(lines.index(to_drop))

    found = False
    for line_nr_of_start_slices, line in enumerate(lines):
        found = '# === IMAGE INFORMATION =' in line
        if found:
            line_nr_of_start_slices += 2
            break
    
    slice_lines = lines[line_nr_of_start_slices:-(skip_rows_eof+1)]
    actual_dyns = len(slice_lines) / int(n_slices)

    if actual_dyns != int(n_dyns):
        warnings.warn("Number of dynamics in PAR-file %s (%s) do not match actual "
                      "dynamics (%i); fixing this ..." % (par, n_dyns, actual_dyns))
        lines[line_nr_of_dyns] = lines[line_nr_of_dyns].replace(n_dyns, str(int(actual_dyns)))

    with open(par, 'w') as f_out:
        [f_out.write(line) for line in lines]

