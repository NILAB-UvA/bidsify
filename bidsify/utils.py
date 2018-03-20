import platform
import subprocess
import os
import json
import gzip
import shutil
import os.path as op
from glob import glob


def check_executable(executable):
    """ Checks if executable is available.

    Params
    ------
    executable : str
        Command to check.

    Returns
    -------
    bool
    """
    cmd = "where" if platform.system() == "Windows" else "which"

    with open(os.devnull, 'w') as devnull:
        res = subprocess.call([cmd, executable], stdout=devnull)

    if res == 0:
        return True
    else:
        return False


def _append_to_json(json_path, to_append):

    if op.isfile(json_path):

        with open(json_path, 'r') as metadata_file:
            metadata = json.load(metadata_file)
            metadata.update(to_append)  # note: this overwrites if key exists!
    else:
        msg = "Constructing new meta-data json (%s)" % json_path
        print(msg)
        metadata = to_append

    with open(json_path, 'w') as new_metadata_file:
        json.dump(metadata, new_metadata_file, indent=4)


def _compress(f, pigz):

    if pigz:
        cmd = ['pigz', f]
        with open(os.devnull, 'w') as devnull:
            subprocess.call(cmd, stdout=devnull)
    else:
        with open(f, 'rb') as f_in, gzip.open(f + '.gz', 'wb') as f_out:
            shutil.copyfileobj(f_in, f_out)
        os.remove(f)


def _make_dir(path):
    """ Creates dir-if-not-exists-already. """

    if not op.isdir(path):
        os.makedirs(path)

    return path


def _glob(path, wildcards):
    """ Finds files with different wildcards. """

    files = []
    for w in wildcards:
        files.extend(glob(op.join(path, '*%s' % w)))

    return sorted(files)


def _run_cmd(cmd, verbose=False, outfile=None):

    if verbose:
        if outfile is None:
            rs = subprocess.call(cmd)
        else:
            with open(outfile, 'w') as f:
                rs = subprocess.call(cmd, stdout=f)
    else:
        with open(os.devnull, 'w') as devnull:
            rs = subprocess.call(cmd, stdout=devnull)

    return rs
