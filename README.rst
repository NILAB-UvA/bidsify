BidsConverter - converts your (raw) data to the BIDS-format
=============================================================

.. _BIDS: http://bids.neuroimaging.io/

This package offers a tool to convert your raw (f)MRI data to the
"Brain Imaging Data Structuce" (BIDS_) format. Using only a 
simple json config-file, it renames, reformats, and restructures 
your files such that it fits the BIDS naming scheme and conforms 
to file-formats specified by BIDS.

Installing BidsConverter
------------------------
For now, it can only be installer from Github, by either cloning 
this repository directory or installing it using `pip`::

    $ pip install git+https://github.com/lukassnoek/BidsConverter.git@master
