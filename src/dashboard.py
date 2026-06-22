"""
The backend for the *dashboard*, allowing reading stat files and stamps for data
and updating them all in a single location. 
"""

# Add local directory to path. 
import os 
import sys 
dname = os.path.dirname(__file__)
sys.path.append(dname)
assert os.path.exists(f"{dname}/stats"), f"{dname}/stats" 
sys.path.append(f"{dname}/stats")

# Import required scripts. 
from stats import get_stats


if __name__ == "__main__":
    # Get all the stats.
    stats = get_stats()
    print(stats["anime"])
