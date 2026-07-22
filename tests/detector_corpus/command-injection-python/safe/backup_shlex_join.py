"""Build a command line from user pieces with shlex.join, which quotes each."""
import subprocess
import shlex


def archive(directory):
    # shlex.join shell-quotes every element, so the directory cannot break out
    # of its argument even though the whole line is run with shell=True.
    cmd = shlex.join(["tar", "czf", "backup.tgz", directory])
    subprocess.check_call(cmd, shell=True)
