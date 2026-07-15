"""Run a fixed maintenance script through an explicit shell, argv list."""
import subprocess


def daily_report():
    # The shell script is a constant, so `sh -c` has nothing user-controlled to
    # interpret even though a shell is invoked.
    return subprocess.check_output(
        ["/bin/sh", "-c", "df -h && uptime"]).decode()
