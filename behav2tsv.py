from __future__ import print_function
import json
import os
import os.path as op
import pandas as pd
import numpy as np
from glob import glob
from nipype.interfaces.base import Bunch
# Presentation-logfile converter

class PresentationLogfileCrawler(object):
    """ Parses a Presentation logfile.

    Logfile crawler for Presentation (Neurobs) files.

    To do: extract parametric weight is specified
    """

    def __init__(self, in_file, con_names, con_codes, con_duration=None,
                 pulsecode=30, verbose=True):

        # in_file can be a single file or list of files
        if isinstance(in_file, str):
            in_file = [in_file]

        self.in_file = in_file
        self.con_names = con_names
        self.con_codes = con_codes

        # Also con_duration needs to be converted to list
        if con_duration is not None:

            if isinstance(con_duration, (int, float)):
                con_duration = [con_duration]

            # If con_duration is the same for all conditions, expand
            if len(con_duration) < len(con_names):
                con_duration = con_duration * len(con_names)

        self.con_duration = con_duration
        self.pulsecode = pulsecode
        self.verbose = verbose
        self.df = None
        self.to_write = None
        self.base_dir = None

    def clean(self):
        print('This should be implemented for a specific, subclassed crawler!')
        # set self.df to cleaned dataframe
        pass

    def parse(self):

        subject_info_list = [self._parse(f) for f in self.in_file]

        if len(subject_info_list) == 1:
            return subject_info_list[0]
        else:
            return subject_info_list

    def _parse(self, f):

        if self.verbose:
            print('Processing %s' % f)

        # Remove existing .bfsl files
        self.base_dir = op.dirname(f)
        _ = [os.remove(x) for x in glob(op.join(self.base_dir, '*.bfsl'))]

        # If .clean() has not been called (and thus logfile hasn't been loaded,
        # load in the logfile now.
        if self.df is not None:
            df = self.df
        else:
            df = pd.read_table(f, sep='\t', skiprows=3,
                               skip_blank_lines=True)

        # Clean up unnecessary columns
        to_drop = ['Uncertainty', 'Subject', 'Trial', 'Uncertainty.1', 'ReqTime',
                   'ReqDur', 'Stim Type', 'Pair Index']
        _ = [df.drop(col, axis=1, inplace=True) for col in to_drop if col in df.columns]

        # Ugly hack to find pulsecode, because some numeric codes are written as str
        df['Code'] = df['Code'].astype(str)
        df['Code'] = [np.float(x) if x.isdigit() else x for x in df['Code']]
        pulse_idx = np.where(df['Code'] == self.pulsecode)[0]

        if len(pulse_idx) > 1: # take first pulse if multiple pulses are logged
            pulse_idx = int(pulse_idx[0])

        # pulse_t = absolute time of first pulse
        pulse_t = df['Time'][df['Code'] == self.pulsecode].iloc[0]
        df['Time'] = (df['Time'] - float(pulse_t)) / 10000.0
        df['Duration'] = df['Duration'] / 10000.0

        df_list = []

        # Loop over condition-codes to find indices/times/durations
        for i, code in enumerate(self.con_codes):

            to_write = pd.DataFrame()

            if type(code) == str:
                code = [code]

            if len(code) > 1:
                # Code is list of integers
                if all(isinstance(c, int) for c in code):
                    idx = df['Code'].isin(code)
                # Code is list of strings
                elif all(isinstance(c, str) for c in code):
                    idx = [any(c in x for c in code) if isinstance(x, str) else False for x in df['Code']]
                    idx = np.array(idx)

            elif len(code) == 1 and type(code[0]) == str:
                # Code is single string
                idx = [code[0] in x if type(x) == str else False for x in df['Code']]
                idx = np.array(idx)
            else:
                # Code is integer
                idx = df['Code'] == code

            if idx.sum() == 0:
                raise ValueError('No entries found for code: %r' % code)

            # Generate dataframe with time, duration, and weight given idx
            to_write['onset'] = df['Time'][idx]

            if self.con_duration is None:
                to_write['duration'] = df['Duration'][idx]
                n_nan = np.sum(np.isnan(to_write['duration']))
                if n_nan > 1:
                    msg = 'In total, %i NaNs found for Duration. Specify duration manually.' % n_nan
                    raise ValueError(msg)

                to_write['duration'] = [np.round(x, decimals=2) for x in to_write['duration']]
            else:
                to_write['duration'] = [self.con_duration[i]] * idx.sum()

            to_write['weight'] = np.ones((np.sum(idx), 1))
            to_write['trail_type'] = [self.con_names[i] for j in range(idx.sum())]

            df_list.append(pd.DataFrame(to_write))

        df = pd.concat(df_list).sort_values(by='onset', axis=0)
        fn = op.join(op.dirname(f), op.splitext(op.basename(f))[0])
        df.to_csv(fn + '.tsv', sep='\t', index=None)

if __name__ == '__main__':

    ex_dir = op.join(op.dirname(op.dirname(op.abspath(__file__))), 'examples')
    test_log = op.join(ex_dir, 'data', 'example_preslog.log')
    con_names = ['A', 'B', 'C']
    con_codes = [range(100, 200),range(200, 300), range(300, 400)]
    plc = PresentationLogfileCrawler(in_file=test_log, con_names=con_names,
                                     con_codes=con_codes)
    plc.parse()