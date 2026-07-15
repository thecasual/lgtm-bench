"""Run a maintenance action selected from a fixed command table."""
import os

COMMANDS = {
    "flush": "systemctl reload nginx",
    "restart": "systemctl restart nginx",
    "status": "systemctl status nginx",
}


def run_action(action):
    # Look the literal command up in the allowlist table.
    cmd = COMMANDS[action]
    os.system(cmd)
