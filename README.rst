``bidsify`` - converts your (raw) data to the BIDS-format
=============================================================

.. _BIDS: http://bids.neuroimaging.io/

.. image:: https://travis-ci.org/spinoza-rec/bidsify.svg?branch=master
    :target: https://travis-ci.org/spinoza-rec/bidsify
 
.. image:: https://ci.appveyor.com/api/projects/status/d9a7bjjqg204kofm?svg=true
    :target: https://ci.appveyor.com/project/lukassnoek/bidsify

.. image:: https://coveralls.io/repos/github/spinoza-rec/bidsify/badge.svg?branch=master
    :target: https://coveralls.io/github/spinoza-rec/bidsify?branch=master

.. image:: https://img.shields.io/badge/python-3.6-blue.svg
    :target: https://www.python.org/downloads/release/python-360

This package offers a tool to convert your raw (f)MRI data to the "Brain Imaging Data Structuce" (BIDS_) format. Using only a simple (json or yaml) config-file, it renames, reformats, and restructures your files such that it fits the BIDS naming scheme and conforms to file-formats specified by BIDS. After using ``bidsify``, you can run your data through BIDS-compatible analysis/preprocessing pipelines such as `fmriprep <http://fmriprep.readthedocs.io/en/latest/>`_
and `mriqc <http://mriqc.readthedocs.io>`_ package.

Currently, we use ``bidsify`` at the Spinoza Centre for Neuroimaging (location REC) to convert data to BIDS after each scan-session. We automated this process, including automatic preprocessing and quality control, using another package, `nitools <https://github.com/spinoza-rec/nitools>`_ (which essentially "glues together" ``bidsify``, ``fmriprep``, and ``mriqc``). 

This package was originally developed to handle MRI-data from Philips scanners, which are traditionally exported
in the "PAR/REC" format. Currently, ``bidsify`` also supports Philips (enhanced) DICOM (``DICOM``/``DICOMDIR`` format) and Siemens DICOM (``.dcm`` extension), but the latter has not been fully tested yet! 

``bidsify`` is still very much in development, so there are probably still some bugs for data
that differs from our standard format (at the Spinoza Centre in Amsterdam) and the API might change
in the future. If you encounter any issues, please submit an issue or (better yet), submit a pull-request
with your proposed solution!

Installing ``bidsify`` & dependencies
---------------------------------------
This package can be installed using ``pip``::

    $ pip install bidsify

To get the "bleeding edge" version, you can install the master branch from github::

    $ pip install git+https://github.com/spinoza-rec/bidsify.git@master

In terms of dependencies: ``bidsify`` uses `dcm2niix <https://github.com/rordenlab/dcm2niix>`_
under the hood to convert PAR/REC and DICOM files to nifti. Make sure you're using release `v1.0.20181125 <https://github.com/rordenlab/dcm2niix/releases/tag/v1.0.20181125>`_ or newer.

Apart from ``dcm2niix``, ``bidsify`` depends on the following Python packages:

- nibabel
- scipy
- numpy
- joblib (for parallelization)
- pandas

Moreover, if you want to use the defacing option (i.e., removing facial features from anatomical images), make sure you have `FSL <https://fsl.fmrib.ox.ac.uk>`_ installed, as well as the `pydeface <https://github.com/poldracklab/pydeface>`_ Python package. Also, to enable validating the BIDS-conversion process,(i.e., running ``bidsify`` with the ``-v`` flag), make sure to install `bids-validator <https://github.com/bids-standard/bids-validator>`_. 

Lastly, if you want to use the Docker interface (i.e., running ``bidsify`` with the `-D` flag), which obviates the need for installing dcm2niix/FSL/bids-validator, make sure to install Docker and make sure your user account has permission to run Docker (see below).

Using Docker
------------
The current version (master branch) allows you to run ``bidsify`` from docker, so you don't
have to install all the (large) dependencies (FSL, pydeface, dcm2niix, bids-validator, etc.). To do so,
you need to do the following.

1. Install Docker (if you haven't already) and make sure you have permission to run Docker;
2. Pull the Docker image: ``docker pull lukassnoek/bidsify:0.x.x`` (fill in the latest version at the x.x);
3. Run bidsify with the `-D` flag (e.g., ``bidsify -c /home/user/config.yml -d /home/user/data -D``)

Now you can use ``bidsify`` even without having FSL, dcm2niix, and other dependencies installed!
(You do need to install ``bidsify`` itself though.)

How does it work?
-----------------
After installing, the ``bidsify`` command can be called as follows::

    $ bidsify [-c config_file] [-d path_to_data_directory] [-o output_directory] [-v] [-D]

The ``-c`` flag defaults to ``config.yml`` in the current working directory.

The ``-d`` flag defaults to the current working directory.

The ``-o`` flag defaults to the parent-directory of the data-directory.

The ``-v`` flag calls `bids-validator <https://github.com/INCF/bids-validator>`_ after BIDS-conversion (optional).

The ``-D`` flag runs ``bidsify`` from Docker (recommended; see "Docker" section above).

For example, if you would call the following command ... ::

    $ bidsify -c /home/user/data/config.yml -d /home/user/data

... your bidsified data will be in the following location::

    /home/user
            ├── data
            |   ├── config.yml
            |   ├── s01
            |   └── s02
            |
            └── bids
                ├── dataset_description.json
                ├── participants.tsv
                ├── sub-01
                └── sub-02

Features
--------
This package aims to take in any MRI-dataset and convert it to BIDS using information from the
config-file provided by the user. Obviously, ``bidsify`` cannot handle *all* types of scans/data,
but it can process most of the default scans/files we use at our MRI centre (Spinoza Centre), including

- Standard (gradient-echo) EPI scans, both multiband and sequential
- Standard (spin-echo) DWI scans
- "Pepolar" (gradient-echo) EPI scans (also called "topup")
- B0-based fieldmap scans (1 phase-difference + 1 magnitude image)
- T1-weighted and T2-weighted scans

``bidsify`` can handle both PAR/REC and DICOM files. Moreover, in the future we want to enable processing of:

- Philips physiology-files ("SCANPHYSLOG" files; WIP, not functional yet)

In terms of "structure", this package allows the following "types" of datasets:

- Multi-subject, multi-session datasets

The config file
---------------
``bidsify`` only needs a config-file in either the json or YAML format. This file should contain
information that can be used to rename and convert the raw files. 

The config file contains a couple of sections, which
are explained below (we'll use the YAML format).

"options"
~~~~~~~~~
The first (top-level) section (or "attribute" in JSON/YAML-lingo) in the file
is the `"options"` section. An example of this section could be:

.. code-block:: yaml

    options:
      mri_ext: PAR  # alternatives: DICOM, dcm, nifti
      debug: False
      n_cores: -1
      subject_stem: sub
      deface: True
      spinoza_data: True
      out_dir: bids

No options *need* to be set explicitly as they all have sensible defaults.
The attribute-value pairs mean the following:

- ``mri_type``: filetype of MRI-scans (PAR, dcm, DICOM, nifti; default: PAR)
- ``n_cores``: how many CPUs to use during conversion (default: -1, all CPUs)
- ``debug``: whether to print extra output for debugging (default: False)
- ``subject_stem``: prefix for subject-directories, e.g. "subject" in "subject-001" (default: sub)
- ``deface``: whether to deface the data (default: True, takes substantially longer though)
- ``spinoza_data``: whether data is from the `Spinoza centre <https://www.spinozacentre.nl>`_ (default: False)
- ``out_dir``: name of directory to save results to (default: bids), relative to project-root.

Note that with respect to DICOM files, the ``mri_type`` can be set to ``DICOM`` (referring to Philips [enhanced] DICOM files) or ``dcm`` (referring to Siemens DICOM files with the extension ``.dcm``).

"mappings"
~~~~~~~~~~
The BIDS-format specifies the naming and format of several types of MRI(-related) filetypes.
These filetypes have specific suffixes, which are appended to the filenames in the renaming
process handled by ``bidsify``. The `"mappings"` section in the config is meant to
tell ``bidsify`` what filetype can be identified by which "key". Thus, the mappings
section consists of `"filetype": "identifier"` pairs. Basically, if BIDS requires a
specific suffix for a filetype, you need to specify that here. For example, a standard
dataset with several BOLD-fMRI files, a T1, and physiological recordings could have
a mappings section like this:

.. code-block:: yaml

    options:
      # ............. #
       
    mappings:
      bold: _func
      T1w: 3DT1
      dwi: DWI
      physio: ppuresp
      events: log
      phasediff: _ph
      magnitude: _mag
      epi: topup
      T2w: T2w

Note that *every file should belong to one, and only one, file-type*! In other words, ``bidsify`` should be able to figure out what kind of file it's dealing with from the filename. For example, if you have a file named ``my_mri_file.PAR`` and you have configured the mappings as in the example above, ``bidsify`` won't be able to figure out what file-type it's dealing with (a ``bold`` file? A ``T1w`` file?), because the filename does not contain *any* of the mappings (e.g., ``_func``, ``3DT1``, or ``DWI``).

Moreover, the filename should not contain *more than one file-type identifier*! Suppose you have a file named ``workingmemory_func_ppuresp.nii.gz``; with the above mappings, ``bidsify`` would conclude that it's either a ``bold`` file (because the name contains ``_func``) OR a ``physio`` file (because the name contains ``ppuresp``). As such, ``bidsify`` is going to skip converting/renaming this file and move it to the `unallocated` directory. In summary: files should contain one, and *only one*, identifier (such as ``_func``) mapping to a particular file-type (e.g., ``bold``). 

Also, check the BIDS-specification for all filetypes supported by the format.

"metadata"
~~~~~~~~~~
At the same (hierarchical) level as the "mappings" and "options" sections, a section
with the name "metadata" can be optionally specified. This attribute may contain an
arbitrary amount of attribute-value pairs which will be appended to **each**
JSON-metadata file during the conversion. These are thus "dataset-general" metadata
parameters. For example, you could specify the data of conversion here, if you'd like:

.. code-block:: yaml

    options:
      # some options
        
    mappings:
      # some mappings
        
    metadata:
      MagneticFieldStrength: 3
      ParallelAcquisitionTechnique: SENSE
      InstitutionName: Spinoza Centre for Neuroimaging, location REC

The ``func``, ``anat``, ``dwi``, and ``fmap`` sections
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
After the ``options``, ``mappings``, and (optionally) the ``metadata`` sections,
the specifications for the four general "BIDS-datatypes" - ``func``, ``anat``, ``dwi``, and ``fmap`` -
are listed in separate sections.

Each section, like ``func``, can contain multiple sub-sections referring to different scans
for that datatype. For example, you could have two different functional runs
with each a different task ("workingmemory" and "nback"). In that case, the "func"
section could look like:

.. code-block:: yaml

    options:
      # some options
        
    mappings:
      # some mappings

    func:

      wm-task:
        id: wmtask
        task: workingmemory

      nback-task:
        id: nbacktask
        task: nback

The exact naming of the "attributes" (here: ``wm-task`` and ``nback-task``) of the sub-sections
do not matter, but the subsequent key-value pairs *do* matter. You *always* need to set the ``id``
key, which is used to identify the files that belong to this particular task. Any key-value pair
besides the ``id`` key-value pair are append to the renamed filename along the BIDS-format.

For example, suppose you have a raw file ``sub-001_wmtask.PAR``. With the above config-file, this file
will be renamed into ``sub-001_task-workingmemory_bold.nii.gz``.

As discussed, *any* key-value pair besides ``id`` will be appended (in the format "key-value") to the
filename during the renaming-process. Imagine, for example, that you have only one task - "nback" - but
you acquired four runs of it per subject, of which the first two were acquired with a sequential acquisition protocol,
but the last two with a multiband protocol (e.g. if you'd want to do some methodological comparison).

The config-file should, in that case, look like:

.. code-block:: yaml

    options:
      # some options
        
    mappings:
      # some mappings

    func:

      nback-task1:
        id: nback1
        task: nback
        run: 1
        acq: sequential

      nback-task2:
        id: nback1
        task: nback
        run: 2
        acq: sequential

      nback-task3:
        id: nback3
        task: nback
        run: 3
        acq: multiband

      nback-task4:
        id: nback4
        task: nback
        run: 4
        acq: multiband

``bidsify`` will then create four files (assuming that they can be "found" using their corresponding ``id``s):

- ``sub-001_task-nback_run-1_acq-sequential_bold.nii.gz``
- ``sub-001_task-nback_run-2_acq-sequential_bold.nii.gz``
- ``sub-001_task-nback_run-3_acq-multiband_bold.nii.gz``
- ``sub-001_task-nback_run-4_acq-multiband_bold.nii.gz``

The same logic can be applied to the "dwi", "anat", and "fmap" sections. For example, if you would have
two T1-weighted structural scans, the "anat" section could look like:

.. code-block:: yaml

    options:
      # some options
        
    mappings:
      # some mappings

    anat:
    
      firstT1:
        id: 3DT1_1
        run: 1

        secondT1:
          id: 3DT1_2
          run: 2

Importantly, any UNIX-style wildcard (e.g. \*, ?, and [a,A,1-9]) can be used in the
``id`` values in these sections!

Lastly, apart from the different elements (such as ``nback-task1`` in the previous example),
each datatype-section (``func``, ``anat``, ``fmap``, and ``dwi``) also may include a
``metadata`` section, similar to the "toplevel" ``metadata`` section. This field may
include key-value pairs that will be appended to *each* JSON-file within that
datatype. This is especially nice if you'd want to add metadata that is needed for
specific preprocessing/analysis pipelines that are based on the BIDS-format.
For example, the `fmriprep <fmriprep.readthedocs.io>`_ package provides
preprocessing pipelines for BIDS-datasets, but sometimes need specific metadata.
For example, for each BOLD-fMRI file, it needs a field ``EffectiveEchoSpacing`` in the
corresponding JSON-file, and for B0-files (one phasediff, one magnitude image) it needs
the fields ``EchoTime1`` and ``EchoTime2``. To include those metadata fields in the
corresponding JSON-files, just include a ``metadata`` field under the appropriate
datatype section. For example, to do so for the previous examples:

.. code-block:: yaml

    func:
    
      metadata:
        EffectiveEchoSpacing: 0.00365
        PhaseEncodingDirection: "j"

      nback:
        id: nback
        task: nback

    fmap:
    
      metadata:
        EchoTime1: 0.003
        EchoTime2: 0.008

      B0: 
        id: B0

How to use ``bidsify``
----------------------
After installing this package, the ``bidsify`` command should be available.
This command assumes a specific organization of your directory with raw data.
Below, I outlined the assumed structure for a simple dataset with one BOLD run and one T1-weighted scan across
two sessions::

    /home/user/data/
                ├── config.yml
                ├── sub-01
                │   ├── ses-1
                │   │   ├── boldrun1.PAR
                │   │   ├── boldrun1.REC
                │   │   ├── T1.PAR
                │   │   └── T1.REC
                │   └── ses-2
                │       ├── boldrun1.PAR
                │       ├── boldrun1.REC
                │       ├── T1.PAR
                │       └── T1.REC
                └── sub-02
                    ├── ses-1
                    │   ├── boldrun1.PAR
                    │   ├── boldrun1.REC
                    │   ├── T1.PAR
                    │   └── T1.REC
                    └── ses-2
                        ├── boldrun1.PAR
                        ├── boldrun1.REC
                        ├── T1.PAR
                        └── T1.REC

(If you have DICOM-files with the ``.dcm`` extension, just replace the PAR/REC files with a single `dcm` file.)

So all raw files should be in a **single** directory, which can be the subject-directory or, optionally,
a session-directory. **Note**: the session directory **must** be named "ses-<something>".
