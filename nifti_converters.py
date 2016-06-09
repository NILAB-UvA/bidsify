from __future__ import print_function
import os
import os.path as op
import numpy as np
import gzip
import shutil
import json
import nibabel as nib

def parrec2nii(PAR_file, compress=True):

    base_dir = op.dirname(PAR_file)
    base_name = op.join(base_dir, op.splitext(PAR_file)[0])

    REC_file = '%s.REC' % op.splitext(PAR_file)[0]

    if not op.exists(base_name + '.nii') and not op.exists(base_name + '.nii.gz'):

        with open(PAR_file, 'r') as f:
            hdr = nib.parrec.parse_PAR_header(f)[0]

        for key, value in hdr.iteritems():

            if isinstance(value, (np.ndarray, np.generic)):
                hdr[key] = value.tolist()

        parts = op.basename(base_name).split('_')
        task_pair = [pair for pair in parts if 'task' in pair]
        task_name = task_pair[0].split('-')[-1] if task_pair else 'no task'

        hdr_json = {'RepetitionTime': hdr['repetition_time'] / 1000,
                    'TaskName': task_name}

        fn = base_name + '.json'

        with open(fn, 'w') as to_write:
            json.dump(hdr_json, to_write, indent=4)

        PR_obj = nib.parrec.load(REC_file)
        nib.nifti1.save(PR_obj, base_name)
        ni_name = base_name + '.nii'

        if compress:
            with open(ni_name, 'rb') as f_in, gzip.open(ni_name + '.gz', 'wb') as f_out:
                shutil.copyfileobj(f_in, f_out)

    _ = [os.remove(f) for f in [REC_file] + [PAR_file] + [ni_name]]
