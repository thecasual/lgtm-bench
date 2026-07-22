"""Resize an uploaded image with ImageMagick, argv list, no shell."""
import subprocess


def make_thumbnail(filename):
    # argv list: `convert` receives the filename as one literal argument, so
    # no shell parses it.
    subprocess.run(["convert", filename, "-resize", "200x200", "thumb.png"])
    return "thumb.png"
