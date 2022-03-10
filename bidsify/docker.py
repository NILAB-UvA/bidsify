import os
import subprocess
import os.path as op
from datetime import datetime
from .utils import _run_cmd
from .version import __version__


def run_from_docker(cfg_path, directory, out_dir, validate, spinoza, uid=None, nolog=False, name=None):
    """ Runs bidsify from Docker. """

    if name is None:
        today = datetime.now().strftime("%Y%m%d")
        basedir = op.basename(op.dirname(directory))
        name = 'bidsify_%s_%s' % (basedir, today)

    proj_name = op.basename(op.dirname(directory))
    date = str(datetime.now().strftime("%Y-%m-%d"))
    if not nolog:
        if spinoza:
            log_file = op.join(op.dirname(op.dirname(out_dir)), 'logs', 'project-%s_stage-bidsify_%s' % (proj_name, date))
        else:
            log_file = op.join(out_dir, 'log')

        print("Writing logfile to %s ..." % log_file)
    
    if uid is None:
        uid = str(os.getuid())  # note: if run by CRON, this is root!
    else:
        str(uid)

    cmd = ['docker', 'run', '--rm',
           '-u', uid + ':' + uid,
           '-v', '%s:/data' % directory,
           '-v', '%s:/config.yml' % cfg_path,
           '-v', '%s:/bids' % out_dir,
           #'--name %s' % name,
           'lukassnoek/bidsify:%s' % __version__, 'bidsify', '-c', '/config.yml', '-d', '/data', '-o', '/bids']

    if validate:
        cmd.append('-v')

    if spinoza:
        cmd.append('-s')

    if not op.isdir(out_dir):
        # Need to create dir beforehand, otherwise it's owned by root
        os.makedirs(out_dir)


    print("RUNNING:")
    print(' '.join(cmd))

    if not nolog:
        fout = open(log_file + '_stdout.txt', 'w')
        ferr = open(log_file + '_stderr.txt', 'w')
        subprocess.run(cmd, stdout=fout, stderr=ferr)
        fout.close()
        ferr.close()
    else:
        subprocess.run(cmd)
