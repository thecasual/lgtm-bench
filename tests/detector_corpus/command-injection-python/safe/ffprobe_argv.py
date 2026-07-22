"""Inspect a media file with ffprobe, argv list."""
import subprocess


def probe(path):
    return subprocess.check_output(
        ["ffprobe", "-v", "quiet", "-show_format", path]).decode()
