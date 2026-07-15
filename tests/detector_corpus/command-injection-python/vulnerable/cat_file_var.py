"""Print a file whose name comes from the request; command built in a var."""
import subprocess


def dump(fname):
    cmd = f"cat {fname}"
    subprocess.run(cmd, shell=True)
