"""Count lines in a user-named log file, argv list."""
import subprocess


def line_count(logfile):
    out = subprocess.check_output(["wc", "-l", logfile]).decode()
    return int(out.strip().split()[0])
