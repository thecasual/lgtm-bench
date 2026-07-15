"""Emit a fixed status line assembled with str.join (all pieces constant)."""
import os


def announce():
    # Every fragment is a literal, so the joined command line is constant.
    os.system(" ".join(["echo", "backup", "complete"]))
