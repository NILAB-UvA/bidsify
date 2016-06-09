from __future__ import print_function
import os
import os.path as op
import json
import pandas as pd
import numpy as np
from glob import glob
from copy import copy, deepcopy

class PresentationLogfileCrawler(object):
    """ Parses a Presentation logfile.

    Logfile crawler for Presentation (Neurobs) files.

    To do: extract parametric weight is specified
    """

    def __init__(self, in_file, event_dir, verbose=True):

        self.in_file = in_file
        self.verbose = verbose
        self.event_dir = event_dir
        self.cfg = None
        self.pulsecode = None
        self.df = None
        self.to_write = None
        self.base_dir = None

    def clean(self):
        print('This should be implemented for a specific, subclassed crawler!')
        # set self.df to cleaned dataframe
        pass

    def _load_task_info(self):
        fn_pairs = op.basename(self.in_file).split('_')
        task_id = [p.split('-')[-1] for p in fn_pairs if 'task' in p][0]

        cfg_files = glob(op.join(self.event_dir, '*.json'))
        cfg = [c for c in cfg_files if task_id in c]
        if not cfg or len(cfg) > 1:
            msg = 'Not a single task.json file found! Found: %r' % cfg
            raise ValueError(msg)

        with open(cfg[0]) as tmp:
            self.cfg = json.load(tmp)

    def _convert_to_range(self):

        self.cfg['con_codes'] = [range(c[0], c[1]) for c in self.cfg['con_codes']]

    def parse(self):
        self._load_task_info()
        self._convert_to_range()

        con_names = self.cfg['con_names']
        con_codes = self.cfg['con_codes']
        con_durations = self.cfg['con_durations']
        con_durations = None if con_durations == "" else con_durations

        try:
            pulsecode = self.cfg['pulsecode']
        except KeyError:
            pulsecode = 30

        if con_durations is not None:

            if isinstance(con_durations, (int, float)):
                con_durations = [con_durations]

            if len(con_durations) < len(con_names):
                con_durations = con_durations * len(con_names)

        f = self.in_file
        base_dir = op.dirname(f)

        # If .clean() has not been called (and thus logfile hasn't been loaded,
        # load in the logfile now.
        if self.df is not None:
            df = self.df
        else:
            df = pd.read_table(f, sep='\t', skiprows=3,
                               skip_blank_lines=True)
        # Clean up unnecessary columns (use list-compr to check if col exists)
        to_drop = ['Uncertainty', 'Subject', 'Trial', 'Uncertainty.1', 'ReqTime',
                   'ReqDur', 'Stim Type', 'Pair Index']
        _ = [df.drop(col, axis=1, inplace=True) for col in to_drop if col in df.columns]

        # Ugly hack to find pulsecode, because some numeric codes are written as str
        df['Code'] = df['Code'].astype(str)
        df['Code'] = [np.float(x) if x.isdigit() else x for x in df['Code']]
        pulse_idx = np.where(df['Code'] == pulsecode)[0]

        if len(pulse_idx) > 1:  # take first pulse if multiple pulses are logged
            pulse_idx = int(pulse_idx[0])

        # pulse_t = absolute time of first pulse
        pulse_t = df['Time'][df['Code'] == pulsecode].iloc[0]
        df['Time'] = (df['Time'] - float(pulse_t)) / 10000.0
        df['Duration'] = df['Duration'] / 10000.0

        df_list = []

        # Loop over condition-codes to find indices/times/durations
        for i, code in enumerate(con_codes):

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

            if con_durations is None:
                to_write['duration'] = df['Duration'][idx]
                n_nan = np.sum(np.isnan(to_write['duration']))
                if n_nan > 1:
                    msg = 'In total, %i NaNs found for Duration. Specify duration manually.' % n_nan
                    raise ValueError(msg)

                to_write['duration'] = [np.round(x, decimals=2) for x in to_write['duration']]
            else:
                to_write['duration'] = [con_durations[i]] * idx.sum()

            to_write['weight'] = np.ones((np.sum(idx), 1))
            to_write['trail_type'] = [con_names[i] for j in range(idx.sum())]

            df_list.append(pd.DataFrame(to_write))

        df = pd.concat(df_list).sort_values(by='onset', axis=0)
        fn = op.join(op.dirname(f), op.splitext(op.basename(f))[0])
        df.to_csv(fn + '.tsv', sep='\t', index=None)
        os.remove(self.in_file)

if __name__ == '__main__':

    test_log = '/home/lukas/test_bids/sub-002/func/sub-002_task-TaskOne_acq-multiband_events.log'
    events_dir = '/home/lukas/test_bids/task_info'
    plc = PresentationLogfileCrawler(in_file=test_log, event_dir=events_dir)
    plc.parse()