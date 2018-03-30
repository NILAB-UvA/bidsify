from .utils import _run_cmd


def run_from_docker(cfg, in_dir, out_dir, validate):
    """ Runs BidsConverter from Docker. """

    cmd = ['docker', 'run', '-it', '--rm', '-v', '%s:/data' % in_dir, '-v',
           '%s:/config.json:ro' % cfg, '-v', '%s:/out' % out_dir,
           'bidsconverter:latest', '-c', '/config.json', '-d', '/data']
    cmd = cmd + " -v" if validate else cmd
    print(' '.join(cmd))
    _run_cmd(cmd, verbose=True)
