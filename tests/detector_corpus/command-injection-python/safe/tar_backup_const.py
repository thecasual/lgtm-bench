"""Kick off a nightly backup of a fixed directory."""
import subprocess


def start_backup():
    # Fully constant command line: nothing user-controlled.
    proc = subprocess.Popen("tar czf backup.tgz /var/data", shell=True)
    return proc.pid
