"""Search a file for a user-supplied pattern via an explicit shell invocation."""
import subprocess


def find_matches(pattern):
    # The argv list looks safe, but the first element is a shell and `-c` hands
    # the following string to it, so the interpolated pattern is parsed by sh.
    return subprocess.check_output(
        ["sh", "-c", f"grep {pattern} /var/log/app.log"]).decode()
