"""Count the lines in a user-named log file with `wc -l`."""
import os


def line_count(logfile):
    out = os.popen(f"wc -l {logfile}").read()
    return int(out.strip().split()[0])
