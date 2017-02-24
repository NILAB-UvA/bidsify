import platform
import subprocess
import os
import json
import os.path as op


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


def append_to_json(json_path, to_append):

    if op.isfile(json_path):

        with open(json_path, 'r') as metadata_file:
            metadata = json.load(metadata_file)
            metadata.update(to_append)  # note: this overwrites if key exists!
    else:
        metadata = to_append

    with open(json_path, 'w') as new_metadata_file:
        json.dump(metadata, new_metadata_file, indent=4)
