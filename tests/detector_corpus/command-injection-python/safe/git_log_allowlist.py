"""Show recent commits for a branch, checked against an allowlist first."""
import subprocess

ALLOWED_BRANCHES = {"main", "develop", "release"}


def recent_commits(branch):
    if branch not in ALLOWED_BRANCHES:
        raise ValueError("unknown branch")
    return subprocess.check_output(
        f"git log --oneline -5 {branch}", shell=True).decode()
