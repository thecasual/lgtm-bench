"""Resolve a domain the user typed via nslookup."""
import os


def resolve(domain):
    # Build the command by concatenation, then run it.
    os.system("nslookup " + domain)
