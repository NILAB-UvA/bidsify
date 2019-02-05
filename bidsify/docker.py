from .utils import _run_cmd
from .version import __version__


def run_from_docker(cfg_path, directory, out_dir, validate, spinoza):
    """ Runs bidsify from Docker. """
    
    cmd = ['docker', 'run', '--rm', '-v', '%s:/data' % directory, '-v',
           '%s:/config.yml' % cfg_path, '-v', '%s:/bids' % out_dir,
           'lukassnoek/bidsify:%s' % __version__, 'bidsify', '-c', '/config.yml', '-d', '/data', '-o', '/bids']

    if validate:
        cmd.append('-v')

    if spinoza:
        cmd.append('-s')

    print("RUNNING:")
    print(' '.join(cmd))
    _run_cmd(cmd, verbose=True)
