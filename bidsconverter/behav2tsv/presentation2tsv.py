from __future__ import print_function, unicode_literals
import os
import os.path as op
import json
import pandas as pd
import numpy as np
from glob import glob
from numbers import Number

NUM_TYPE = (np.float64, np.float32, np.float, np.int, np.int64, np.int16, float, int)


class Pres2tsv(object):
    """ Parses a Presentation logfile.

    Logfile crawler for Presentation (Neurobs) files.

    To do: extract parametric weight is specified
    """

    def __init__(self, in_file, event_dir, verbose=True):

        self.in_file = in_file
        self.verbose = verbose
        self.event_dir = event_dir
        self.cfg = None
        self.cfg_loaded = False
        self.pulsecode = None
        self.df = None
        self.to_write = None
        self.base_dir = None

    def _load_task_info(self):
        fn_pairs = op.basename(self.in_file).split('_')
        task_id = [p.split('-')[-1] for p in fn_pairs if 'task' in p][0]

        cfg_files = glob(op.join(self.event_dir, '*.json'))
        cfg = [c for c in cfg_files if task_id in c]
        if not cfg or len(cfg) > 1:
            msg = "Not a single {task}.json file found for task '%s'! Found: %r. Skipping ..." % (task_id, cfg)
            print(msg)
            skip = True
        else:
            with open(cfg[0]) as tmp:
                self.cfg = json.load(tmp)
            skip = False

        return skip

    def _convert_to_range(self):

        c_codes = []
        for c in self.cfg['con_codes']:

            if not isinstance(c, list):
                c_codes.append(c)

            elif isinstance(c, list):

                if all(isinstance(s, str) for s in c):
                    c_codes.append(c)
                elif all(isinstance(s, list) for s in c):

                    tmp_codes = []

                    for ci in c:
                        tmp_codes.extend(np.arange(ci[0], ci[1] + 1, dtype=np.int))
                    c_codes.append(tmp_codes)
                else:
                    c_codes.append(np.arange(c[0], c[1] + 1, dtype=np.int))

        self.cfg['con_codes'] = c_codes
        self.cfg_loaded = True

    def parse(self):
        skip = self._load_task_info()
        if skip:
            return 0

        if not self.cfg_loaded:
            self._convert_to_range()

        con_names = self.cfg['con_names']
        con_codes = self.cfg['con_codes']
        con_durations = self.cfg['con_durations']
        con_durations = None if con_durations == "" else con_durations

        try:
            pulsecode = self.cfg['pulsecode']
        except KeyError:
            pulsecode = 255

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
            df = pd.read_table(f, sep=str('\t'), skiprows=3,
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

        if 'event_type' in self.cfg.keys():
            df = df[df['Event Type'] == self.cfg['event_type']]
        df_list = []

        # Loop over condition-codes to find indices/times/durations

        for i, code in enumerate(con_codes):
            to_write = pd.DataFrame()

            if not isinstance(code, (list, np.ndarray)):
                code = [code]

            if len(code) > 1:
                # Code is list of possibilities
                if all(isinstance(c, NUM_TYPE) for c in code):
                    idx = df['Code'].isin(code)

                elif all(isinstance(c, str) for c in code):
                    idx = [any(c in x for c in code) if isinstance(x, str)
                           else False for x in df['Code']]

                    idx = np.array(idx)

            elif len(code) == 1 and isinstance(code[0], str):
                # Code is single string
                idx = [code[0] in x if type(x) == str else False for x in df['Code']]
                idx = np.array(idx)
            else:
                idx = df['Code'] == code[0]

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
            to_write['trial_type'] = [con_names[i] for j in np.arange(idx.sum())]

            df_list.append(pd.DataFrame(to_write))

        df = pd.concat(df_list).sort_values(by='onset', axis=0)
        fn = op.join(op.dirname(f), op.splitext(op.basename(f))[0])
        df.to_csv(fn + '.tsv', sep=str('\t'), index=None)
        os.remove(self.in_file)
