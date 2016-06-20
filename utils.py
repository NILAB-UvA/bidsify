import platform
import subprocess
import os

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