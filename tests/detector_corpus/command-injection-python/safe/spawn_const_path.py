"""List a directory by spawning a fixed program."""
import os


def listing(directory):
    # Program path is a constant; the directory is just an argument to it.
    return os.spawnv(os.P_WAIT, "/bin/ls", ["/bin/ls", "-la", directory])
