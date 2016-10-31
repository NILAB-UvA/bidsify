import os
import os.path as op
import numpy as np
import pandas as pd


def convert_phy(f):

    df = pd.read_csv(f, sep=' ', skiprows=5, header=None)
    df.dropna(axis=1, inplace=True, how='all')
    header = open(testphy, "r")
    linelist = header.readlines()
    header = linelist[4].replace('#', '').rstrip().split(' ')
    df.columns = [s for s in header if s]

    gradients = ['gx', 'gy', 'gz']
    gradient_signal = np.array([df[g] for g in gradients]).sum(axis=0)
    gradient_signal[np.isnan(gradient_signal)] = 0
    gradient_signal = (gradient_signal - gradient_signal.mean()) / gradient_signal.std()

    fn = op.join(op.dirname(f), op.splitext(op.basename(f))[0])
    df.to_csv(fn + '.tsv.gz', sep='\t', index=None, compression='gzip')
    os.remove(f)

if __name__ == '__main__':

    testphy = '/media/lukas/data/Spynoza_data/data_piop/sub-0028/func/sub-0028_task-harriri_acq-sequential_physio.phy'

