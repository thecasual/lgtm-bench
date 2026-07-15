"""Show recent commits for a branch name the caller passes."""
import subprocess


def recent_commits(branch):
    # Last five commits on the requested branch, oneline format.
    return subprocess.check_output(
        f"git log --oneline -5 {branch}", shell=True).decode()
