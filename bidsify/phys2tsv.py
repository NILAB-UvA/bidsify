import os
import os.path as op
import numpy as np
import pandas as pd


def convert_phy(f):

    '''
    try:  # Try to skip 5 rows (new version)
        df = pd.read_csv(f, delim_whitespace=True, skiprows=5, header=0,
                         low_memory=False)
        _ = df['gx']
    except KeyError:  # Else skip 4 rows (old version)
        df = pd.read_csv(f, delim_whitespace=True, skiprows=4, header=0,
                         low_memory=False)

    gradients = ['gx', 'gy', 'gz']
    gradient_signal = np.array([df[g] for g in gradients]).sum(axis=0)
    gradient_signal[np.isnan(gradient_signal)] = 0
    centered = gradient_signal - gradient_signal.mean()
    gradient_signal = centered / gradient_signal.std()

    fn = op.join(op.dirname(f), op.splitext(op.basename(f))[0])

    # Ideally, create sidecar-json with following fields:
    # "SamplingFrequency": 100.0,
    # "StartTime": -22.345,
    # "Columns": ["cardiac", "respiratory", "trigger"]

    df.to_csv(fn + '.tsv.gz', sep='\t', index=None, compression='gzip')
    os.remove(f)
    '''
    pass
