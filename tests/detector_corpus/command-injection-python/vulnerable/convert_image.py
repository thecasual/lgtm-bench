"""Resize an uploaded image with ImageMagick."""
import subprocess


def make_thumbnail(filename):
    # Shell out to `convert` to produce a 200px thumbnail.
    subprocess.run(f"convert {filename} -resize 200x200 thumb.png", shell=True)
    return "thumb.png"
