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
assert os.path.exists(f"{dname}/stamps"), f"{dname}/stamps"
sys.path.append(f"{dname}/stamps")

# Import required scripts. 
from stampinterface import get_stamps
from stats import get_stats


if __name__ == "__main__":
    # Get all the stats. The stamp-checking condition will check this. 
    stats = get_stats() 
    
    # Now, check the status of all automated stamps.
    stamps = get_stamps()
    for stamp in stamps:
        if "progress" in stamp and stamp["progress"] is not None:
            print(stamp["id"], eval(stamp["progress"]))
