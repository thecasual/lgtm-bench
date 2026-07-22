"""Run systemctl only for an allowlisted action name."""
import os

ALLOWED = {"start", "stop", "restart"}


def control(action):
    if action in ALLOWED:
        os.system(f"systemctl {action} nginx")
        return True
    return False
