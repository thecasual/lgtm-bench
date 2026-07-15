"""Report disk usage of a path from the request."""
import subprocess


def usage(path):
    # `du -sh` gives a human-readable total for the folder.
    return subprocess.call("du -sh {}".format(path), shell=True)
