"""
Utility functions that others may need. 
"""

import os

from pathlib import Path 


def get_git_root(cwd=__file__) -> str:
    """
    Walk upwards from the current path until we find a path with ".git" in it.
    Raises an exception if ".git" cannot be found.
    """
    
    start = os.path.abspath(cwd)
    cwd = start
    while True:
        if os.path.exists(f"{cwd}/.git"):
            return cwd 
        else:
            basedir = os.path.dirname(cwd)
            if cwd == basedir:
                raise FileNotFoundError(f"No .git directory from \"{start}\"")
            cwd = basedir
