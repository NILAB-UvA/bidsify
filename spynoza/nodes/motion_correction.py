# Some functions to use as Nipype-nodes.

from __future__ import division, print_function


def find_middle_run(in_files):
    """ Finds middle run based on Philips Achieva run/exam card numbering.

    Kind of ugly, but works

    Parameters
    ----------
    in_files : list[str]
        List of absolute paths to nifti-files.

    Returns
    -------
    middle_run : str
        Absolute path to middle run.
    other_runs : list[str]
        List with absolute paths to the other runs.
    """

    import numpy as np

    idx = np.hstack([np.where(np.array(x.split('_')) == 'SENSE')[0] + 1 for x in in_files])
    run_nrs = np.array([int(x.split('_')[i]) for x, i in zip(in_files, idx)])
    middle_run = np.where(np.median(run_nrs) == run_nrs)[0][0]
    other_runs = [x for x in in_files if x != middle_run]

    return middle_run, other_runs


def mcflirt_across_runs(in_file, cost='mutualinfo', stages=3):
    """ Motion-correction based on middle-run, within one function.

    Takes list of in_files and performs motion-correction on middle run,
    calculates its mean-bold (average across time) and uses this as a
    reference to motion-correct the other runs.

    Parameters
    ----------
    in_file : str
        Absolute path to nifti-file.
    cost : str
        Cost to use in motion-correction algorithm (see nipype documentation).
    stages : int
        Number of stages in motion-correction (see nipype documentation).

    Returns
    -------
    out_files : list[str]
        List of absolute paths to motion-corrected files.
    mean_bold : str
        Absolute path to mean-bold volume.
    plot_files : list
        List of paths to par-files created during motion-correction.

    NOTE: instead of using this function, it's better to use find_middle_run
    as a node and connect this to individual MCFLIRT nodes.
    """

    import numpy as np
    from nipype.interfaces.fsl import MCFLIRT
    import os
    import nibabel as nib

    mc_files = []
    plot_files = []

    middle_run, other_runs = find_middle_run(in_file)
    middle_data = nib.load(middle_run)

    new_name = os.path.basename(middle_run).split('.')[:-2][0] + '_mc.nii.gz'
    out_name = os.path.abspath(new_name)

    mcflt = MCFLIRT(in_file=middle_run, cost=cost,
                    interpolation='sinc', out_file=out_name, stages=stages,
                    save_plots=True)

    results = mcflt.run(in_file=middle_run)

    mc_files.append(out_name)
    plot_files.append(results.outputs.par_file)

    mean_bold_path = os.path.abspath('mean_bold.nii.gz')
    _ = os.system('fslmaths %s -Tmean %s' % (out_name, mean_bold_path))

    for other_run in other_runs:

        new_name = os.path.basename(other_run).split('.')[:-2][0] + '_mc.nii.gz'
        out_name = os.path.abspath(new_name)

        mcflt = MCFLIRT(in_file=other_run, cost=cost, ref_file=mean_bold_path,
                        interpolation='sinc', out_file=out_name, stages=stages,
                        save_plots=True)

        results = mcflt.run()
        mc_files.append(out_name)
        plot_files.append(results.outputs.par_file)

    out_files = mc_files
    mean_bold = mean_bold_path

    return out_files, mean_bold, plot_files
