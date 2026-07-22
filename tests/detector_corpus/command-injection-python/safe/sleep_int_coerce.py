"""Pause for a caller-supplied number of seconds."""
import os


def wait(seconds):
    # int() coercion: the interpolated value can only be a number.
    os.system(f"sleep {int(seconds)}")
