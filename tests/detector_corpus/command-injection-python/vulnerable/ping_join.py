"""Ping a host the user typed, command assembled with str.join."""
import os


def is_reachable(host):
    # Join the argv fragments into one shell line. Because os.system runs the
    # whole string through /bin/sh, the joined host is interpreted by the shell.
    return os.system(" ".join(["ping", "-c", "1", host])) == 0
