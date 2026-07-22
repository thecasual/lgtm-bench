"""Delete a scratch path supplied by the caller."""
import os


def cleanup(path):
    # Percent-format the path into an rm command.
    os.system("rm -rf %s" % path)
