"""Check reachability of a host the user typed, shell-quoted."""
import os
import shlex


def is_reachable(host):
    return os.system("ping -c 1 " + shlex.quote(host)) == 0
