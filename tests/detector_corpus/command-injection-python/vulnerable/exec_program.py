"""Run a program the user selected by name."""
import os


def launch(userbin, target):
    # Replace the current process image with the requested program.
    os.execvp(userbin, [userbin, target])
