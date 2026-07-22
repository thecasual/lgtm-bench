"""List a user-named directory via the commands shell wrapper."""
import commands


def listing(directory):
    return commands.getoutput(f"ls -la {directory}")
