"""Show the first N lines of a fixed log; N coerced to an integer."""
import subprocess


def head(n):
    cmd = "head -n " + str(int(n)) + " /var/log/app.log"
    return subprocess.check_output(cmd, shell=True).decode()
