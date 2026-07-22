"""Kick off a backup by shelling out to tar with a user-chosen directory."""
import subprocess


def start_backup(directory):
    proc = subprocess.Popen(
        f"tar czf backup.tgz {directory}", shell=True)
    return proc.pid
