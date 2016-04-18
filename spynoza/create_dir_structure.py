"""
This module contains functions to set-up the analysis directory structure
for preprocessing. It assumes that there is a project directory (project_dir)
containing subject-specific subdirectories with all corresponding files. A
working directory is created with subject-specific subdirecties, which in turn
contain directories for separate "runs" (e.g. T1, func_A, func_B1, func_B2).

ONLY USED FOR examples/simple_workflow.ipynb!
"""

from __future__ import division, print_function
import os
from glob import glob
import shutil
import cPickle
import nibabel as nib
import os.path as op
import urllib
import subprocess


class DataOrganizer(object):
    """ Organizes data into a sensible directory structure.

    Class that performs minor preprocessing (PAR/REC to nifti conversion) and
    creates a project tree that is sensible given a Nipype preprocessing
    workflow.
    """

    def __init__(self, run_names, project_dir=None, subject_stem='sub',
                 already_converted=False):
        """ Initializes a DataOrganizer object.

        Parameters
        ----------
        run_names : dictionary
            Dictionary with type of scan as keys (functional, structural, B1,
            etc.) and keywords/identifiers as values
            (e.g. 'functional': 'runx').
        project_dir : str (default: current dir)
            Which directory to convert/process.
        subject_stem : str
            Prefix of subject names / directories.
        already_converted : bool (default: False)
            Whether PAR/RECs have already been converted to nifti (takes a
            while, so only convert when necessary.
        """
        self.run_names = run_names

        if project_dir is None:
            project_dir = os.getcwd()
        self.project_dir = project_dir
        self.working_dir = op.join(project_dir, 'working_directory')
        self.subject_stem = subject_stem
        self.subject_dirs = glob(op.join(project_dir, '%s*' % subject_stem))

        if not self.subject_dirs and not already_converted:
            raise ValueError('Could not find valid subject directories!')

        if already_converted:
            self.subject_dirs = glob(op.join(self.working_dir, '*%s*' %
                                             subject_stem))

    def fetch_test_data(self):

        url = 'https://db.tt/KCemtca7'
        out_file = op.join('%s' % self.project_dir, 'test_data.zip')

        if not op.isdir(op.dirname(out_file)):
            os.makedirs(op.dirname(out_file))

        if op.exists(op.join(self.project_dir, 'test_data')):
            self.project_dir = op.join(op.dirname(out_file), 'test_data')
            self.working_dir = op.join(self.project_dir, 'working_directory')
            self.subject_dirs = glob(op.join(self.project_dir, '%s*' % self.subject_stem))

            return 'Already downloaded!'

        msg = """ The file you will download is 523 MB; do you want to continue?
                  (Y / N) """
        resp = raw_input(msg)

        if resp in ['Y', 'y', 'yes', 'Yes']:
            print('Downloading test data ...', end='')

            if not op.exists(out_file):
                urllib.urlretrieve(url, out_file)

            with open(os.devnull, 'w') as devnull:
                out_dir = op.dirname(out_file)
                subprocess.call(['unzip', out_file, '-d', out_dir], stdout=devnull)
                subprocess.call(['rm', out_file], stdout=devnull)

                print(' done.')
                print('Data is located at: %s' % op.join(out_dir, 'test_data'))

        elif resp in ['N', 'n', 'no', 'No']:
            print('Aborting download.')
        else:
            print('Invalid answer! Choose Y or N.')

        self.project_dir = op.join(op.dirname(out_file), 'test_data')
        self.working_dir = op.join(self.project_dir, 'working_directory')
        self.subject_dirs = glob(op.join(self.project_dir, '%s*' % self.subject_stem))

    def convert_parrec2nifti(self, remove_nifti=True):
        """ Converts PAR/REC files to nifti-files. """

        if not op.isdir(self.working_dir):
            os.makedirs(self.working_dir)

        new_sub_dirs = []
        for sub_dir in self.subject_dirs:
            REC_files = glob(op.join(sub_dir, '*.REC'))
            PAR_files = glob(op.join(sub_dir, '*.PAR'))

            # Create scaninfo from PAR and convert .REC to nifti
            for REC, PAR in zip(REC_files, PAR_files):

                self.create_scaninfo(PAR)
                REC_name = REC[:-4]

                if not op.exists(REC_name + '.nii'):
                    print("Processing file %s ..." % REC_name, end="")
                    PR_obj = nib.parrec.load(REC)
                    nib.nifti1.save(PR_obj,REC_name)
                    print(" done.")

                else:
                    print("File %s was already converted." % REC_name)

            niftis = glob(op.join(sub_dir, '*.nii'))

            if niftis:
                os.system('gzip %s' % op.join(sub_dir, '*.nii'))

            if remove_nifti:
                os.system('rm %s' % op.join(sub_dir, '*.nii'))

            new_dir = op.join(self.working_dir, op.basename(sub_dir))
            shutil.copytree(sub_dir, new_dir)
            shutil.rmtree(sub_dir)
            new_sub_dirs.append(new_dir)

        self.subject_dirs = new_sub_dirs
        print("Done with conversion of par/rec to nifti.")

    def create_project_tree(self):
        """
        Moves files to subject specific directories and creates run-specific
        subdirectories
        """

        for sub_dir in self.subject_dirs:

            for func_run in self.run_names['func']:

                func_dir = op.join(sub_dir, 'func_%s' % func_run)
                if not op.isdir(func_dir):
                    os.makedirs(func_dir)

                # kinda ugly, but it works (accounts for different spellings)
                run_files = glob(op.join(sub_dir, '*%s*' % func_run))
                run_files.extend(glob(op.join(sub_dir, '*%s*' % func_run.upper())))
                run_files.extend(glob(op.join(sub_dir, '*%s*' % func_run.capitalize())))

                _ = [shutil.move(f, func_dir) for f in run_files]

            struc_run = self.run_names['struc']
            struc_dir = op.join(sub_dir, struc_run)
            if not op.isdir(struc_dir):
                os.makedirs(struc_dir)

            struc_files = glob(op.join(sub_dir, '*%s*' % struc_run))

            _ = [shutil.move(f, struc_dir) for f in struc_files]

            unallocated = glob(op.join(sub_dir, '*'))

            for f in unallocated:
                if not op.isdir(f):
                    print('Unallocated file: %s' % f)

    def reset_pipeline(self):
        """
        Resets to analysis set-up to raw files aggregated in the project_dir.
        Retrieves log/phy files from ToProcess and PAR/REC from backup_dir.
        Subsequently removes all subdirectories of the project_dir.
        """

        for sub in self.subject_dirs:
            dirs = glob(op.join(sub, '*'))

            for d in dirs:
                if op.isdir(d):

                    files = glob(op.join(d, '*'))
                    _ = [shutil.move(to_move, sub) for to_move in files]

            shutil.copytree(sub, op.join(self.project_dir, op.basename(sub)))
            shutil.rmtree(sub)

        self.subject_dirs = glob(op.join(self.project_dir, '*%s*' % self.subject_stem))

    def create_dir_structure_full(self):
        """ Chains convert_parrec2nifti and create_project_tree. """
        self.convert_parrec2nifti().create_project_tree()

    def get_filepaths(keyword, directory):
        """
        Given a certain keyword (including wildcards), this function walks
        through subdirectories relative to arg directory (i.e. root) and returns
        matches (absolute paths) and filenames_total (filenames).
        """

        matches = []
        filenames_total = []

        for root, dirnames, filenames in os.walk(directory):
            for filename in filenames:
                if keyword in filename:
                    matches.append(root + '/' + filename)
                    filenames_total.append(filename)
        return matches, filenames_total

