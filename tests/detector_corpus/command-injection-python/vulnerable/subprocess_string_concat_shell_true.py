"""Ping a host by concatenating it into a shell command string."""
import subprocess


def is_reachable(host):
    # A string command with shell=True IS the shell string that gets
    # interpreted, so the concatenated host is injectable.
    return subprocess.run("ping -c 1 " + host, shell=True).returncode == 0
