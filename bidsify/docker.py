from .utils import _run_cmd
from .version import __version__


def run_from_docker(cfg, in_dir, out_dir, validate):
    """ Runs BidsConverter from Docker. """

    cmd = ['docker', 'run', '-it', '--rm', '-v', '%s:/data' % in_dir, '-v',
           '%s:/config.yml:ro' % cfg, '-v', '%s:/bids' % out_dir,
           'lukassnoek/bidsify:%s' % __version__, 'bidsify', '-c', '/config.yml', '-d', '/data', '-o', '/bids']

    if validate:
        cmd.append('-v')

    print(' '.join(cmd))
    _run_cmd(cmd, verbose=True)
