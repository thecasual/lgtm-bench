"""Compress a request-supplied path, quoted before interpolation."""
import subprocess
import shlex


def compress(path):
    subprocess.check_call(f"gzip -f {shlex.quote(path)}", shell=True)
    return path + ".gz"
