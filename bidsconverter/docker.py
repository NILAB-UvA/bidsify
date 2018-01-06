from .utils import _run_cmd


def run_from_docker(cfg, in_dir, out_dir, validate):

    cmd = ['docker', 'run', '-it', '--rm', '-v', '%s:/data:ro' % in_dir, '-v',
           '%s:/config.json:ro' % cfg, '-v', '%s:/out' % out_dir,
           'bidsconverter:latest', '-c', '/config.json', '-d', '/data']
    cmd = cmd + " -v" if validate else cmd
    _run_cmd(cmd)
