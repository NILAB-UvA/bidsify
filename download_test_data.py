""" This script fetches test-data for bidsify.
The data is stored at Surfdrive (a data storage repository/drive
from the Dutch institute for IT in science/academia) and downloaded
using cURL. """

from __future__ import print_function
import subprocess
import os
import zipfile
import os.path as op

this_dir = op.dirname(op.realpath(__file__))
dst_dir = op.join(this_dir, 'bidsify', 'data', 'test_data')
dst_file = op.join(dst_dir, 'test_data.zip')

data_file = 'https://surfdrive.surf.nl/files/index.php/s/aQQTSghdmBPbHt7/download'

if not op.isdir(op.join(dst_dir, 'PIOP_1_parrec')):

    print("Downloading the data ...\n")
    cmd = "curl -o %s %s" % (dst_file, data_file)
    return_code = subprocess.call(cmd, shell=True)
    print("\nDone!")
    print("Unzipping ...", end='')
    zip_ref = zipfile.ZipFile(dst_file, 'r')
    zip_ref.extractall(dst_dir)
    zip_ref.close()
    print(" done!")
    os.remove(dst_file)
else:
    print("Data is already downloaded and located at %s/*" % dst_dir)
