"""Compress a file whose path arrives on a request."""
import subprocess


def compress(path):
    # Use the system gzip so the on-disk format matches our other tooling.
    subprocess.check_call(f"gzip -f {path}", shell=True)
    return path + ".gz"
