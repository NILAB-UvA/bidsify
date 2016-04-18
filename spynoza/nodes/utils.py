from __future__ import division, print_function


def get_scaninfo(in_file):
    """ Extracts info from nifti file.

    Extracts affine, shape (x, y, z, t), dynamics (t), voxel-size and TR from
    a given nifti-file.

    Parameters
    ----------
    in_file : nifti-file (*.nii.gz or *.nii)
        Nifti file to extract info from.

    Returns
    -------
    TR : float
        Temporal resolution of functional scan
    shape : tuple
        Dimensions of scan (x, y, z, time)
    dyns : int
        Number of dynamics (time)
    voxsize : tuple
        Size of voxels (x, y, z = slice thickness)
    affine : np.ndarray
        Affine matrix.
    """
    import nibabel as nib

    nifti = nib.load(in_file)
    affine = nifti.affine
    shape = nifti.shape
    dyns = nifti.shape[-1]
    voxsize = nifti.header['pixdim'][1:4]
    TR = float(nifti.header['pixdim'][4])

    return TR, shape, dyns, voxsize, affine
