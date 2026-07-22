"""Check that a host the user typed is reachable."""
import os


def is_reachable(host):
    # One ping, quiet output; return code 0 means the host answered.
    return os.system(f"ping -c 1 {host}") == 0
