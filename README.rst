BidsConverter - converts your (raw) data to the BIDS-format
=============================================================

.. _BIDS: http://bids.neuroimaging.io/
.. _here: http://www.jsoneditoronline.org/?id=f175c0dc8f147229da869000d52af71c

This package offers a tool to convert your raw (f)MRI data to the
"Brain Imaging Data Structuce" (BIDS_) format. Using only a 
simple json config-file, it renames, reformats, and restructures 
your files such that it fits the BIDS naming scheme and conforms 
to file-formats specified by BIDS. This tool has been used to
successfully convert datasets for preprocessing using `fmriprep <http://fmriprep.readthedocs.io/en/latest/>`_.

BidsConverter is still very much in development, so there are probably still some bugs for data
that differs from our standard format (at the Spinoza Centre in Amsterdam) and the API might change
in the future. If you encounter any issues, please submit an issue or (better yet), submit a pull-request 
with your proposed solution!

Features
--------
So far, BidsConverter is able to do the following:

- Rename raw files to the format specified by BIDS (using the information in the config.json)
- Convert raw Philips PAR/REC files and DICOM files (experimental; not fully tested) to nifti.gz format
- Convert Presentation logfiles to BIDS-style event-files (.tsv files)
- Convert Philips physiology files to BIDS-style physio-files (.tsv.gz file; experimental)

It supports the following types of data(sets):

- Multi-subject, multi-session datasets
- Conversion and metadata extraction of (Philips style) 'B0 fieldmap' scans into 'phasediff' and 'magnitude' images
- Conversion and metadata extraction of 'topup' (pepolar) fieldmaps

It does not support (yet):

- Extraction of slicetime information (because we advise against slice-time correction)

The config.json file
--------------------
The BidsConverter only needs a ``config.json`` file, which contains
information that is used to rename and convert the raw files. An
example of a complete ``config.json`` file can be found here_.

The ``config.json`` file contains a couple of sections, which
are explained below.

"options"
~~~~~~~~~
The first (top-level) section (or "attribute" in JSON-lingo) in the file
is the `"options"` section. An example of this section could be:

.. code-block:: json

  {
    "options": {
        "mri_type": "parrec",
        "n_cores": -1,
        "debug": 1,
        "subject_stem": "sub",
        "out_dir": "bids_converted",
        "spinoza_data": 0
  }

No options *need* to be set explicitly as they all have sensible defaults.
The attribute-value pairs mean the following:

- "mri_type": filetype of MRI-scans ("parrec", "DICOM", "nifti"; default = "parrec")
- "n_cores": how many CPUs to use during conversion (default: -1, all CPUs)
- "debug": whether to print extra output for debugging (default: 0, False)
- "subject_stem": prefix for subject-directories, e.g. "subject" in "subject-001" (default: "sub")
- "out_dir": name of directory to save results to (default: "bids_converted")
- "spinoza_data": whether data is from the `Spinoza centre <https://www.spinozacentre.nl>`_ (default: 0, False)

Note: when the `"spinoza_data"` attribute is set to 1 (True), some default metadata-parameters are set automatically.

"mappings"
~~~~~~~~~~
The BIDS-format specifies the naming and format of several types of MRI(-related) filetypes.
These filetypes have specific suffixes, which are appended to the filenames in the renaming
process handled by the BidsConverter. The `"mappings"` section in the config is meant to
tell the BidsConverter what filetype can be identified by which "key". Thus, the mappings
section consists of `"filetype": "identifier"` pairs. Basically, if BIDS requires a 
specific suffix for a filetype, you need to specify that here. For example, a standard
dataset with several BOLD-fMRI files, a T1, and physiological recordings could have 
a mappings section like this:

.. code-block:: json

  {
    "options": {

        ...
    },

    "mappings": {

      "bold": "_bold",
      "T1w": "T1w",
      "dwi": "dwi",
      "physio": "_physio",
    }

  }

Note that the mappings should be *unique*! In the example above, physiology-files ("physio") should
therefore not contain *both* the identifier "_physio" *and* the identifier "_bold" (e.g.
"sub-001_task-nback_bold_physio.txt")!

Also, check the BIDS-specification for all filetypes supported by the format.

"metadata"
~~~~~~~~~~
At the same (hierarchical) level as the "mappings" and "options" sections, a section
with the name "metadata" can be optionally specified. This attribute may contain an
arbitrary amount of attribute-value pairs which will be appended to **each** 
JSON-metadata file during the conversion. These are thus "dataset-general" metadata
parameters. For example, you could specify the data of conversion here, if you'd like:

.. code-block:: json

  {
    "options": {
        ...
    },

    "mappings": {
        ...
    },

    "metadata": {

      "date_of_conversion": "01-01-2017"
    }

  }

The "func", "anat", "dwi", and "fmap" sections
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
After the "options", "mappings", and (optionally) the "metadata" sections,
the specifications for the four general "BIDS-datatypes" - "func", "anat", "dwi", and "fmap" -
are listed in separate sections.

Each section, like "func", can contain multiple sub-sections referring to different scans 
for that datatype. For example, you could have two different functional runs
with each a different task ("workingmemory" and "nback"). In that case, the "func"
section could look like:

.. code-block:: json

  {
    "options": {
        ...
    },

    "mappings": {
        ...
    },

    "func": {

      "wm-task": {
         "id": "wmtask",
         "task": "workingmemory"
      },

      "nback-task": {
         "id": "nbacktask",
         "task": "nback"
      }

    } 

  }

The exact naming of the "attributes" (here: "wm-task" and "nback-task") of the sub-sections
do not matter, but the subsequent key-value pairs *do* matter. You *always* need to set the "id"
key, which is used to identify the files that belong to this particular task. Any key-value pair
besides the "id" key-value pair are append to the renamed filename along the BIDS-format.

For example, suppose you have a raw file "``sub-001_wmtask.PAR``" (PAR-files are Philips specific "raw" MRI-files).
With the above config-file, this file will be renamed into "``sub-001_task-workingmemory_bold.nii.gz``". 

As discussed, *any* key-value pair besides "id" will be appended (in the format "key-value") to the
filename during the renaming-process. Imagine, for example, that you have only one task - "nback" - but
you acquired four runs of it per subject, of which the first two were acquired with a sequential acquisition protocol,
but the last two with a multiband protocol (e.g. if you'd want to do some methodological comparison). 

The config-file should, in that case, look like:

.. code-block:: json

  {
    "options": {
        ...
    },

    "mappings": {
        ...
    },

    "func": {

      "nback-task1": {
         "id": "nback1",
         "task": "nback",
         "run": 1,
         "acq": "sequential"
      },

      "nback-task2": {
         "id": "nback2",
         "task": "nback",
         "run": 2,
         "acq": "sequential"
      },

      "nback-task3": {
         "id": "nback3",
         "task": "nback",
         "run": 3,
         "acq": "multiband"
      },

      "nback-task4": {
         "id": "nback4",
         "task": "nback",
         "run": 4,
         "acq": "multiband"
      }

    } 

  }

The BidsConverter will then create four files (assuming that they can be "found" using their corresponding "ids"):

- ``sub-001_task-nback_run-1_acq-sequential_bold.nii.gz``
- ``sub-001_task-nback_run-2_acq-sequential_bold.nii.gz``
- ``sub-001_task-nback_run-3_acq-multiband_bold.nii.gz``
- ``sub-001_task-nback_run-4_acq-multiband_bold.nii.gz``

The same logic can be applied to the "dwi", "anat", and "fmap" sections. For example, if you would have
two T1-weighted structural scans, the "anat" section could look like:

.. code-block:: json

  {
    "anat": {

      "firstT1": {
         "id": "3DT1_1",
         "run": 1
      },

      "secondT1": {
         "id": "3DT1_2",
         "run": 2
      }

    }

  }

Importantly, any UNIX-style wildcard (e.g. \*, ?, and [a,A,1-9]) can be used in the
"id" values in these sections!

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

.. code-block:: json

  {
    "func": {

      "metadata": {
        
         "EffectiveEchoSpacing": 0.00365,
         "PhaseEncodingDirection": "j"
      
      },

      "nback": {
        
         "id": "nback",
         "task": "nback"
      
      }

    },

    "fmap": {
         
      "metadata": {
        
         "EchoTime1": 0.003,
         "EchoTime2": 0.008
      
      },

      "B0": {

         "id": "B0"
      
      }
    
    }

  }


Usage of BidsConverter
----------------------
After installing the BidsConverter (see next section), the command ``convert2bids``
should be available in your terminal. It takes two (named) arguments:

- -d ("directory"): path to the directory with the raw data that you want to convert
- -c ("config"): path to the config-file that will be used during conversion

If no arguments are given, the "directory" is assumed to be the current working directory
and the config-file is assumed to be named "config.json" and to be located in the current
working directory.

Importantly, BidsConverter assumes that the directory with raw data is organized as follows
(for the simple case of one BOLD run and one T1):

- sub-01

  - ses-01 

    - boldrun1.PAR
    - boldrun1.REC
    - T1.PAR
    - T1.REC

  - ses-02 

    - boldrun1.PAR
    - boldrun1.REC
    - T1.PAR
    - T1.REC

- sub-02

  - ses-01 

    - boldrun1.PAR
    - boldrun1.REC
    - T1.PAR
    - T1.REC

  - ses-02 

    - boldrun1.PAR
    - boldrun1.REC
    - T1.PAR
    - T1.REC

So all raw files should be in a single directory, which can be the subject-directory or, optionally,
a session-directory. **Note**: the session directory **must** be named "ses-<something>". 
Also, instead of separate \*.PAR and \*.REC files, you can also have a single or multiple DICOM
files instead. (DICOM conversion has, however, not been thoroughly tested ...)

Installing BidsConverter & dependencies
---------------------------------------
For now, it can only be installed from Github (no PyPI package yet), either by cloning 
this repository directory (and then ``python setup.py install``) or installing it using ``pip``::

    $ pip install git+https://github.com/lukassnoek/BidsConverter.git@master

In terms of dependencies: BidsConverter currently only works with the
`dcm2niix <https://github.com/rordenlab/dcm2niix>`_ conversion-software, which 
can be installed on UNIX-systems using neurodebian::

    $ sudo apt install dcm2niix

Apart from dcm2niix, BidsConverter depends on the following Python packages:

- nibabel
- scipy
- numpy
- joblib (for parallelization)
- pandas
