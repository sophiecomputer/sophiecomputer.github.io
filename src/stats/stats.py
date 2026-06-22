"""
Manages reading the stat files and parsing them into usable data. To keep the 
public website and private stat data files separate, we use a private ".env" 
file in this same directory which is *not committed* to the GitHub. This 
contains the path to each data file. The data files are the following:
  * anime
  * clean 
  * fruit
  * manga
  * mood
  * office
  * papers
  * productivity
  * screentime
  * sleep
  * vegetable
  * workout
The ".env" file is a line-separated file containing strings in the format
"keyword:path", where "keyword" is one of hte above and "path" is from the 
system root. Each markdown stat file has a YAML frontmatter describing its data
format.
"""

# Add local directory to path. 
import os 
import sys 
dname = os.path.dirname(os.path.dirname(__file__))
sys.path.append(dname)

import datetime 
import re 

from typing import Any, Dict, IO, Iterator, List, Optional, Tuple, Type, Union
from util import get_git_root


class CellStat:
    """
    A *cell* represents a single day on a calendar. A single date may contain
    multiple data points; if the statistic represents papers read, then we may
    read multiple papers in a day. Some dates are null and contain no data. 
    This must be overridden.
    """

    def __init__(self: "CellStat", date: datetime.date, data: Any) -> None:
        """
        Creates a Date object, given the day on the calendar it corresponds to
        and the data it contains. "data" may be None. 
        """

        self.date = date 
        self.data = data 


    def cal_text(self: "CellStat") -> str: 
        """
        Returns ourselves as a string, for calendars which want to display us
        as a multiline output. 
        """

        raise NotImplementedError


    def cal_count(self: "CellStat") -> Union[int, float]:
        """
        Returns ourselves as a number. Some calendars may want to serialize 
        the data for this Date into a single number for displaying. 
        """

        raise NotImplementedError


    def cal_bool(self: "CellStat") -> bool:
        """
        Returns ourselves as a truthy value, for calendars which just want to 
        color a cell according to the presence or absense of something. 
        """

        return self.cal_count() > 0


    def __str__(self: "CellStat") -> str:
        return f"{self.date}: {self.cal_text()}"


    def __repr__(self: "CellStat") -> str:
        return str(self) 


class BoolStat(CellStat):
    """
    Represents a boolean value for each day.
    """
    
    def __init__(
        self: "BoolStat", 
        date: datetime.date, 
        data: Optional[bool]
    ) -> None:
        if data is None: 
            data = False
        super().__init__(date, data)


    def cal_text(self: "BoolStat") -> str:
        return ""  # Don't show True or False in a calendar cell.

    
    def cal_count(self: "BoolStat") -> Union[int, float]:
        return 1 if self.data else 0 


    def cal_bool(self: "BoolStat") -> bool:
        return self.data 


class AccumulateStat(CellStat):
    """
    Represents an accumulation of values for each day.
    """

    def __init__(
        self: "AccumulateStat", 
        date: datetime.date, 
        data: Optional[list[str]]
    ) -> None:
        if data is None:
            data = [] 
        super().__init__(date, data) 

    
    def cal_text(self: "AccumulateStat") -> str:
        return "\n".join(str(s) for s in self.data)


    def cal_count(self: "AccumulateStat") -> Union[int, float]:
        return len(self.data) 


    def cal_bool(self: "AccumulateStat") -> bool:
        return len(self.data) > 0

    
    def append(self: "AccumulateStat", value: str) -> None:
        """
        Appends the value to the list of data we contain. 
        """

        self.data.append(value) 


class ValueStat(CellStat):
    """
    Represents a single value for the day. 
    """

    def __init__(
        self: "ValueStat", 
        date: datetime.date, 
        data: Optional[Union[int, float]]
    ) -> None:
        super().__init__(date, data)  # Propagate None values.
    
    
    def cal_text(self: "ValueStat") -> str:
        return str(self.data)
    
    
    def cal_count(self: "ValueStat") -> Union[int, float]:
        return self.data if self.data is not None else 0


    def cal_bool(self: "ValueStat") -> bool:
        return self.data is not None and self.data > 0 


class ToggletimeStat(CellStat):
    """
    Represents alternating (on, off) values for a day.
    """

    def __init__(
        self: "ToggletimeStat", 
        date: datetime.date, 
        data: Optional[List[Tuple[int, bool]]]
    ) -> None:
        """
        The data is (number of minutes since midnight, True = on / False = off).
        """

        if data is None:
            data = [] 
        super().__init__(date, data)


    def cal_text(self: "ToggletimeStat") -> str:
        raise NotImplementedError  # TODO 


    def cal_count(self: "ToggletimeStat") -> Union[int, float]:
        raise NotImplementedError  # TODO 


    def cal_bool(self: "ToggletimeStat") -> bool:
        raise NotImplementedError  # TODO
            
    
    def append(
        self: "ToggletimeStat", 
        minutes_since_midnight: int, 
        on: bool
    ) -> None:
        """
        Appends the value to the list of data we contain. 
        """

        self.data.append((minutes_since_midnight, on))


class StatCalendar:
    """
    A *calendar* is a collection of date cells (not necessarily aligned to a 
    date boundary, like a month or year).
    """
    
    def __init__(
        self: "StatCalendar", 
        cell_type: Type[CellStat], 
        yaml: Dict[str, str]
    ) -> None:
        self.cells = {}  # Maps datetime.date to a CellStat object.
        self.cell_type = cell_type
        self.iterator = None


    def add(self: "StatCalendar", cell: CellStat) -> None:
        """
        Adds the given cell to our collection of cells.
        """
    
        assert cell.date not in self.cells, f"{cell.date} in {self.cells}"
        self.cells[cell.date] = cell

    
    def get(self: "StatCalendar", date: datetime.date) -> CellStat:
        """
        Returns the cell with the same date as the parameter. If no date exists
        which matches the parameter, then returns a cell of the same instance as 
        our initially-given type with default arguments (representing an empty
        cell) and adds that new empty cell to ourselves.
        """
        
        if date in self.cells:
            return self.cells[date] 
        else:
            new_cell = self.cell_type(date=date, data=None)
            self.cells[date] = new_cell
            return new_cell 
        

    def read(self: "StatCalendar", line: str) -> None:
        """
        Reads a single line from a stat file and updates our internal cells with 
        the contents. Raises an error if the line cannot be parsed.  
        """

        raise NotImplementedError

    
    def __str__(self: "StatCalendar") -> str:
        return "\n".join(str(cell) for cell in self.cells.values())
    

    def __repr__(self: "StatCalendar") -> str:
        return str(self) 


    def __iter__(
        self: "StatCalendar"
    ) -> Iterator[Tuple[datetime.date, CellStat]]:
        return iter(self.cells.items())


class BoolCalendar(StatCalendar):
    """
    Each cell in this calendar represents a boolean value. Each data item is 
    simply a "M/D/Y" date with nothing else (except the string "none").
    """
    
    def __init__(self: "BoolCalendar", yaml: Dict[str, str]) -> None:
        super().__init__(BoolStat, yaml)


    def read(self: "BoolCalendar", line: str) -> None:
        if mat := re.fullmatch(r"(\d+)/(\d+)/(\d+).*", line):
            # Parse the date.
            month, day, year = (
                int(mat[1]), 
                int(mat[2]), 
                int(mat[3])
            )
            if year < 2000:
                year += 2000 
            date = datetime.date(year=year, month=month, day=day)
            
            # If a date is present (and is not None), then it's True. The 
            # super-class "get" method will interpret missing dates as False.
            self.add(BoolStat(date=date, data=True))
        else:
            raise ValueError(f"Cannot parse \"{line}\" as BoolStat")


class AccumulateCalendar(StatCalendar):
    """
    Each cell in this calendar is an accumulation of values, where each value 
    corresponds to a line in the original Markdown file. 
    """

    def __init__(self: "AccumulateCalendar", yaml: Dict[str, str]) -> None:
        super().__init__(AccumulateStat, yaml)


    def read(self: "AccumulateCalendar", line: str) -> None:
        if mat := re.fullmatch(r"(\d+)/(\d+)/(\d+),? (.+)", line): 
            # Parse the date. 
            month, day, year = (
                int(mat[1]), 
                int(mat[2]), 
                int(mat[3])
            )
            if year < 2000:
                year += 2000 
            date = datetime.date(year=year, month=month, day=day)

            # Get the existing value in the calendar. If it already exists, 
            # "get" will return an AccumulateStat with a value in it; if it 
            # doesn't exist, "get" will return a new AccumulateStat with nothing 
            # in it, and add it to itself. 
            acc_cell = self.get(date)

            # Add the new value to this AccumulateStat. 
            value = mat[4]
            acc_cell.append(value)
        else:
            raise ValueError(f"Cannot parse \"{line}\" as AccumulateStat")


class ValueCalendar(StatCalendar):
    """
    Each cell in this calendar is attached with a numeric value. There is one 
    line of Markdown per cell. 
    """

    def __init__(self: "ValueCalendar", yaml: Dict[str, str]) -> None:
        super().__init__(ValueStat, yaml)


    def read(self: "ValueCalendar", line: str) -> None:
        if mat := re.fullmatch(r"(\d+)/(\d+)/(\d+) (\d+\.?\d*).*", line):
            # Parse the date. 
            month, day, year = (
                int(mat[1]), 
                int(mat[2]), 
                int(mat[3])
            )
            if year < 2000:
                year += 2000 
            date = datetime.date(year=year, month=month, day=day)
            
            # Add the date. 
            value = float(mat[4]) if "." in mat[4] else int(mat[4])
            self.add(ValueStat(date=date, data=value))
        else:
            raise ValueError(f"Cannot parse \"{line}\" as ValueStat")


class ToggletimeCalendar(StatCalendar):
    """
    Each cell in this calendar individually represents an accumulation of 
    durations, but it can also be displayed as a collection of (start, stop)
    pairs for some event (like sleeping), renderable on a different kind of 
    hourly calendar. 
    """

    def __init__(self: "ToggletimeCalendar", yaml: Dict[str, str]) -> None: 
        super().__init__(ToggletimeStat, yaml)
        self.on_alias = yaml.get("on-alias", "on") 
        self.off_alias = yaml.get("off-alias", "off")


    def read(self: "ToggletimeCalendar", line: str) -> None:
        if mat := re.fullmatch(
            r"(\d+)/(\d+)/(\d+) ([^\s]+) (\d+):(\d+)(am|pm|AM|PM)", 
            line
        ):
            # Parse the date. 
            month, day, year = (
                int(mat[1]), 
                int(mat[2]), 
                int(mat[3])
            )
            if year < 2000:
                year += 2000 
            date = datetime.date(year=year, month=month, day=day)
            
            # Get the existing value in the calendar. If it already exists, 
            # "get" will return a ToggletimeStat with a value in it; if it 
            # doesn't exist, "get" will return a new ToggletimeStat with nothing 
            # in it, and add it to itself. 
            tt_cell = self.get(date)

            # Parse time part. 
            hour, minute, ampm = (
                int(mat[5]), 
                int(mat[6]), 
                mat[7].lower()
            )
            assert 1 <= hour <= 12, line
            assert 0 <= minute <= 59, line
            
            # Get minutes from midnight. 
            if ampm == "am": hour24 = 0 if hour == 12 else hour
            else:            hour24 = 12 if hour == 12 else hour + 12
            absminute = hour24 * 60 + minute
            
            # Get whether this is "on" or "off".
            specifier = mat[4]
            if specifier not in (self.on_alias, self.off_alias):    
                raise ValueError((
                    f"Unknown specifier \"{specifier}\" for line \"{line}\", "
                    f"expected one of \"{self.on_alias}\" or "
                    f"\"{self.off_alias}\"."
                ))

            # Add the date. 
            tt_cell.append(absminute, specifier)
        else:
            raise ValueError(f"Cannot parse \"{line}\" as ToggletimeStat")


def read_env() -> Dict[str, str]:
    """
    Reads the .env file, which must be present within the same directory as the
    ".git" file. Also ensures the required keywords are present within the .env
    file. 
    """

    git_root = get_git_root()
    env_path = f"{git_root}/.env"
    assert os.path.exists(env_path), f".env file missing at \"{env_path}\""
    
    data = {} 
    with open(env_path, "r") as f:
        # Line separated list of (keyword):(path) entries.
        for line in f: 
            line = line.strip() 
            if ":" not in line: 
                continue

            idx = line.index(":") 
            keyword = line[:idx]
            path = line[idx+1:]
            data[keyword] = path.strip()

            # While we're here, assert the path actually exists.
            assert os.path.exists(path), path 
    
    # Ensure all required keys are provided and no extra keys. 
    req_keys = { 
        "anime", "clean" ,"fruit", "manga", "mood", "office", "papers", 
        "productivity", "screentime", "sleep", "vegetable", "workout"
    }
    cur_keys = set(data.keys()) 
    assert cur_keys == req_keys, (
        repr((cur_keys - req_keys).union(req_keys - cur_keys))
    )
    
    return data


def read_stat_file(path: str) -> StatCalendar: 
    """
    Given the path to a stat file, returns a calendar representing it. The type
    of the stat file is inferred from the YAML frontmatter.
    """
    
    assert os.path.exists(path), path 
    with open(path, "r") as f: 
        # The first line must be the start of YAML frontmatter. 
        assert next(f).strip() == "---", (
            f"Error: \"{path}\" does not have YAML frontmatter."
        )

        # Read until final "---".
        yaml = {}
        for line in f:
            line = line.strip()
            if line == "---":
                break 
            
            assert ":" in line, f"Improper line \"{line}\" in \"{path}\""
            idx = line.index(":")
            keyword = line[:idx]
            data = line[idx+1:] 
            yaml[keyword] = data.strip() 
        else:
            raise ValueError(
                f"File \"{path}\" does not close YAML frontmatter block"
            )

        # The YAML frontmatter must contain a key "type" representing the type 
        # of the stat file.
        assert "type" in yaml.keys(), (
            f"\"type\" not present in YAML for \"{path}\""
        )
        cal_type = yaml["type"]
    
        # Create the instance.
        type_map = {
            "bool": BoolCalendar,
            "accumulate": AccumulateCalendar, 
            "value": ValueCalendar, 
            "toggletime": ToggletimeCalendar 
        }
        if cal_type not in type_map:
            raise ValueError(f"Calendar type \"{cal_type}\" unknown")
        cal = type_map[cal_type](yaml)

        # Read the remainder of the file.
        reading_comment = False 
        for line in f:
            line = line.strip() 
            if line == "%%":
                reading_comment = not reading_comment 
            elif (
                not reading_comment and 
                len(line) > 0 and 
                "none" not in line.lower()
            ):
                try:
                    cal.read(line)
                except Exception as ex:
                    raise RuntimeError((
                        "The following exception occurred as a result of "
                        f"reading the file \"{path}\"."
                    )) from ex

    # Return the final object.
    return cal


class StatDatabase:
    """
    An optional interface for accessing the stats.
    """
    
    def __init__(self: "StatDatabase", env: Dict[str, str]) -> None:
        """
        Creates a database from a collection of (keyword, path) pairs.
        """

        self.stats = {
            key : read_stat_file(path)
            for key, path in env.items()
        }


    def sum(self: "StatDatabase", key: str, days: int) -> Union[float, int]:
        """
        Sums the count of values in the last (days) days for the calendar 
        identified by (key). 
        """

        assert key in self.stats.keys(), f"{key} not in {self.stats.keys()}"
        assert days > 0

        stat = self.stats[key] 

        # Get the last (days) days and sum their values.
        total = 0
        today = datetime.date.today() 
        for i in range(days):
            delta = datetime.timedelta(days=i)
            date = today - delta 
            cell = stat.get(date)
            total += cell.cal_count()
        
        return total 
    

    def count(self: "StatDatabase", key: str, days: int) -> Union[float, int]:
        """
        Counts how many of the last (days) days in the calendar identified by 
        (key) have a True value. 
        """

        assert key in self.stats.keys(), f"{key} not in {self.stats.keys()}"
        assert days > 0

        stat = self.stats[key] 

        # Get the last (days) days and count True values.
        total = 0
        today = datetime.date.today() 
        for i in range(days):
            delta = datetime.timedelta(days=i)
            date = today - delta 
            cell = stat.get(date)
            total += 1 if cell.cal_bool() else 0
        
        return total 


def get_stat(keyword: str) -> StatCalendar: 
    """
    Returns the stat file corresponding to the given keyword.
    """

    # Read the (entire) .env file for the path.
    env = read_env() 
    assert keyword in env.keys(), f"{keyword} not in {env.keys()}"
    
    # Create a singular calendar from the path. 
    return read_stat_file(env[keyword]) 


def get_stats() -> StatDatabase:
    """
    Reads all stat files and obtains their data.
    """
        
    # Read the .env file.
    env = read_env()

    # Create a database out of the stats. We serialize automated hooks in JSON
    # format, so this interface simplifies things.
    return StatDatabase(env)
