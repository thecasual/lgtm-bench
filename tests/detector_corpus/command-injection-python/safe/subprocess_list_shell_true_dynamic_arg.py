"""Ping a host using a list argv even though shell=True is (mistakenly) set."""
import subprocess


def is_reachable(host):
    # With shell=True and a LIST arg, /bin/sh runs only the first element as the
    # command string; the remaining elements (including `host`) become sh's
    # positional params ($0, $1, ...), never interpolated into the command. So
    # this is a bug, not command injection.
    return subprocess.run(
        ["ping", "-c", "1", host], shell=True
    ).returncode == 0
