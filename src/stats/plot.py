"""
Plots a StatCalendar object on a calendar drawing.
"""

# Add local directory to path. 
import os 
import sys 
dname = os.path.dirname(__file__)
sys.path.append(dname)
parent = os.path.dirname(dname) 
sys.path.append(parent) 

import argparse
import calendar
import datetime
import math
import matplotlib.pyplot as plt 
import random 
import re 
import shlex
import subprocess

from collections import defaultdict
from stats import get_stat, get_stats
from typing import Any, Dict, List, Optional, Tuple, Type
from util import get_git_root


SINGLE_COLUMN_WIDTH = 3.33  # Inches
DOUBLE_COLUMN_WIDTH = 6.875 

header_color = "#660066" 
shaded_color = "#bd00ff" 

def config_matplotlib() -> None:
    """
    Configures matplotlib to work well on the paper. 
    """

    plt.rcParams.update({
        "font.family": "serif",
        "font.serif": ["Times New Roman"],  
        "font.size": 9,
        "axes.labelsize": 9,
        "axes.titlesize": 9,
        "xtick.labelsize": 8,
        "ytick.labelsize": 8,
        "legend.fontsize": 8,
        "pdf.fonttype": 42,  # TrueType fonts, good for inclusion in PDFs
        "ps.fonttype": 42,
    })


def color_interpolate(color1: str, color2: str, t: float) -> str:
    """
    Linearly interpolates between two colors.
    """
    
    assert 0.0 <= t <= 1.0, str(t)  

    # Convert to RGB.
    a = tuple(int(color1[i : i+2], 16) for i in (1, 3, 5))
    b = tuple(int(color2[i : i+2], 16) for i in (1, 3, 5))

    # Interpolate each channel.
    interp = tuple(
        round(a[i] + (b[i] - a[i]) * t)
        for i in range(3)
    )
    
    # Reformat as hex.
    return f"#{interp[0]:02x}{interp[1]:02x}{interp[2]:02x}"


def plot_calendar(
    statcal: "StatCalendar", 
    title: str, 
    yearly: bool, 
    firstday: Tuple[int], 
    out_fname: str 
):
    """
    Draws a calendar. "yearly" is True if we plot an entire year or False if we 
    plot a single month. "firstday" is a tuple of (year, month, day), where 
    everything before this day is shaded in gray. "value" must be an enum
    specifier.
    """
    
    first_date = datetime.date(
        year=int(firstday[0]),
        month=int(firstday[1]),
        day=int(firstday[2])
    )

    # First, get the range of values for the gradient.
    min_val = 0
    max_val = float("-inf")
    for date, cell in statcal:
        if cell.cal_bool():
            min_val = min(min_val, cell.cal_count())
            max_val = max(max_val, cell.cal_count())
    
    # Next, create a map of dates (month: int, day: int, year: int) to 
    # (gradient: float [0, 1], text: str) pairs.
    cells = {} 
    for date, cell in statcal:
        key = (date.month, date.day, date.year)
        gradient = (cell.cal_count() - min_val) / (max_val - min_val)
        # text = "\n".join(
        #     line if len(line) <= 5 else line[:6] + "..."
        #     for line in cell.cal_text().split("\n")
        # )
        text = (
            str(cell.cal_count()) if isinstance(cell.cal_count(), int) else 
            f"{cell.cal_count():.1f}"
        )
        cells[key] = (gradient, text) 

    # Get the current year and month.
    current_month = datetime.datetime.now().month
    current_year = datetime.datetime.now().year
    weekday_str = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
    month_str = ["January", "February", "March", "April", "May", "June", "July", 
        "August", "September", "October", "November", "December"]

    # Create the empty table. Create a mapping of a month to the (row, col) of 
    # the table that month should be drawn on.
    fig_size = None
    cell_values = None
    colors = None 
    month_pos = {} 
    if yearly:
        # 3 rows, 4 cols per row, each cell represents a sub-table with 7 rows
        # and 7 cols per row. Add padding between each sub-table (to make it 
        # 8 rows / 8 cols per sub-table).
        rows = 3 * 9 + 1
        cols = 4 * 8 + 1
        fig_size = (DOUBLE_COLUMN_WIDTH * 2, DOUBLE_COLUMN_WIDTH)
        cell_values = [
            ["" for _ in range(cols)] 
            for _ in range(rows)
        ]
        colors = [
            ["black" for _ in range(cols)]
            for _ in range(rows) 
        ]
        month_pos = {
            month_idx + 1 : (month_idx // 4 * 9 + 3, 1 + month_idx % 4 * 8)
            for month_idx in range(12) 
        }
        
        # Set the cells corresponding to dates to white.
        for month, (row, col) in month_pos.items(): 
            first_weekday = datetime.date(
                year=current_year,
                month=month, 
                day=1
            ).weekday() 
            month_days = calendar.monthrange(current_year, month)[-1]
            for i in range(month_days):
                coff = (first_weekday + i) % 7
                roff = (first_weekday + i) // 7
                date = datetime.date(
                    year=current_year,
                    month=month,
                    day=(i + 1)
                )
                colors[row + roff][col + coff] = (
                    "white" if first_date <= date <= datetime.date.today()
                    else "#b5b5b5"
                )
            
            # Set gray areas corresponding to non-dates within a month
            # sub-table. 
            for i in range(first_weekday):
                colors[row][col + i] = "gray"
            count = 7 - ((month_days + first_weekday) % 7)
            for i in range(count):
                i += month_days
                coff = (first_weekday + i) % 7
                roff = (first_weekday + i) // 7
                colors[row + roff][col + coff] = "gray"

            # Set the header colors here, too.
            colors[row - 2][col : col + 7] = ["#ffffff"] * 7
            colors[row - 1][col : col + 7] = [header_color] * 7
            cell_values[row - 1][col : col + 7] = weekday_str
        
        today = datetime.date.today() 
        title += f" ({today.month}/{today.day}/{today.year})"

    else:
        cal = calendar.Calendar(firstweekday=0)
        month_days = len(cal.monthdayscalendar(year, month))
        vpad = DOUBLE_COLUMN_WIDTH / 15 if month_days == 6 else 0
        fig_size = (DOUBLE_COLUMN_WIDTH, DOUBLE_COLUMN_WIDTH / 5 * 2 + vpad) 
        cell_values = [
            ["" for _ in range(7)]
            for _ in range(month_days + 1)
        ]
        colors = [
            ["#ffffff" for _ in range(7)]
            for _ in range(month_days + 1) 
        ]
        cell_values[0][:] = weekday_str
        colors[0][:] = [header_color] * 7
        
        # Darken the cells which do not map to dates.
        first_weekday = datetime.date(
            year=current_year, 
            month=current_month, 
            day=1
        ).weekday() 
        for i in range(0, first_weekday):
            colors[1][i] = "gray" 

        month_pos = { current_month : (1, 0) }
        title += f" ({month_str[current_month - 1]} {current_year})"
    
    # Put the values in each cell.
    for month, (row, col) in month_pos.items():
        # For each item in this month, add the text and set the gradient of 
        # each cell.
        for (
            (cell_month, cell_day, cell_year), 
            (gradient, text) 
        ) in cells.items():
            if cell_month == month and cell_year == current_year:
                # Determine the offset. The calendar always has Monday be the 
                # leftmost cell.
                first_weekday = datetime.date(
                    year=current_year,
                    month=month, 
                    day=1
                ).weekday() 
                day_offset = cell_day - 1
                coff = (first_weekday + day_offset) % 7
                roff = (first_weekday + day_offset) // 7
            else:
                continue

            # Convert month and day to row/column offset.
            colors[row + roff][col + coff] = (
                color_interpolate("#ffffff", shaded_color, gradient)
            )
            cell_values[row + roff][col + coff] = text
    
    config_matplotlib()
    fig, ax = plt.subplots(figsize=fig_size)
    ax.axis('off')
    table = ax.table(
        cellText=cell_values,
        cellColours=colors,
        loc="center",
        cellLoc="center",
        fontsize=(10 if yearly else 16)
    )
    
    # Adjust table style
    table.scale(1, 2.0)

    # Force layout so cell geometry becomes valid. 
    fig.canvas.draw() 
   
    # Add corner text. 
    for month, (row, col) in month_pos.items():
        first_weekday = datetime.date(
            year=current_year,
            month=month, 
            day=1
        ).weekday() 
        month_days = calendar.monthrange(current_year, month)[-1]
        for i in range(month_days):
            coff = (first_weekday + i) % 7
            roff = (first_weekday + i) // 7

            # Cell bounding box 
            cell = table[row + roff, col + coff]
            bbox = cell.get_window_extent(fig.canvas.get_renderer())
            inv = ax.transAxes.inverted()
            x0, y0 = inv.transform((bbox.x0, bbox.y0))
            x1, y1 = inv.transform((bbox.x1, bbox.y1))
            cx = (x0 + x1) / 2
            cy = (y0 + y1) / 2
    
            # Add date number to top-left
            ax.text(
                x0 + 0.002, y1 - 0.01,  # near top-left corner
                str(i + 1),
                ha="left",
                va="top",
                fontsize=(6 if yearly else 10),
                color="black",
                transform=ax.transAxes
            )

        if yearly:
            for coff in range(7):
                table[row - 2, col + coff].set_linewidth(0)
            
            # Cell bounding box 
            cell = table[row - 2, col + 3]
            bbox = cell.get_window_extent(fig.canvas.get_renderer())
            inv = ax.transAxes.inverted()
            x0, y0 = inv.transform((bbox.x0, bbox.y0))
            x1, y1 = inv.transform((bbox.x1, bbox.y1))
            cx = (x0 + x1) / 2
            cy = (y0 + y1) / 2
    
            # Add date number to top-left
            ax.text(
                cx, cy,
                month_str[month - 1],
                ha="center",
                va="center",
                fontsize=14,
                color="black",
                transform=ax.transAxes
            )
    
        # Set the color of the text in the headers.
        for i in range(7):
            table[row - 1, col + i].set_text_props(
                color="#ffffff", 
                fontweight="bold"
            ) 

    fig.subplots_adjust(top=0.85)
    # ax.set_title(("a" * 200 + "\n") * 5, pad=50) 
    ax.set_title(title, pad=(90 if yearly else 2), fontsize=24) 
    fig.tight_layout(pad=0.1)
    plt.savefig(out_fname, dpi=400, bbox_inches="tight") 
    print(f"Figure saved to \"{out_fname}\"")


def get_args() -> Optional[argparse.Namespace]:
    """
    Parses the arguments. If no arguments are provided, returns None. 
    """

    parser = argparse.ArgumentParser(
        description=(
            "When run directly, creates a calendar image from a stat. If no "
            "arguments are provided, generates all stat files."
        )
    )

    if len(sys.argv) == 1:  # Only the executable file passed
        return None    

    def date_type(value):
        if mat := re.fullmatch(r"(\d+)/(\d+)/(\d+)", value):
            month, day, year = (int(mat[1]), int(mat[2]), int(mat[3]))
            if not (1 <= month <= 12) or not (1 <= day <= 31):
                raise argparse.ArgumentTypeError("Invalid date for MM/DD/YY")
            if year < 2000:
                year += 2000
            return (year, month, day)
        else:
            raise argparse.ArgumentTypeError("Invalid date")
    
    parser.add_argument("--stat-keyword", required=True, 
        help="Keyword representing the statistic")
    parser.add_argument("--title", required=True,
        help="Title for the created figure")
    parser.add_argument("--yearly", default=False, action="store_true",
        help="If set, makes this a yearly calendar; otherwise, make it monthly")
    parser.add_argument("--first-day", required=True, type=date_type, 
        help="First day of tracking the stat (i.e., \"1/2/26\")")
    parser.add_argument("--out-fname", required=True, 
        help="Where to write the resulting file")

    return parser.parse_args()


if __name__ == "__main__":
    args = get_args() 
    if args is None:
        # Before we begin, try parsing all the stats. This is faster than going
        # through the below, and reveals errors in formatting before they 
        # happen.
        get_stats()

        def call(
            stat: str, 
            title: str, 
            yearly: bool, 
            firstday: str, 
            out_fname: str
        ):
            """
            Runs a subprocess and returns it.
            """
            
            cmd = [
                sys.executable, os.path.abspath(__file__),
                "--stat-keyword", stat, 
                "--title", title, 
                "--first-day", firstday, 
                "--out-fname", out_fname
            ] + (["--yearly"] if yearly else [])
            print(shlex.join(cmd))
            return subprocess.Popen(cmd)

        # Generate all calendars. This can potentially take some time, so do 
        # them in parallel.
        git_root = get_git_root()
        procs = [call(*args) for args in [
            ("papers", "Papers Read", True, "12/7/25", f"{git_root}/stats/papers.png"),
            ("anime", "Anime Episodes Watched", True, "12/5/25", f"{git_root}/stats/anime.png"),
            ("clean", "Times Cleaned", True, "5/16/26", f"{git_root}/stats/clean.png"),
            ("fruit", "Fruits Eaten", True, "5/4/26", f"{git_root}/stats/fruit.png"),
            ("vegetable", "Vegetables Eaten", True, "5/4/26", f"{git_root}/stats/vegetables.png"),
            ("workout", "Times Worked Out", True, "1/25/26", f"{git_root}/stats/workout.png"),
            ("mood", "Mood", True, "4/23/26", f"{git_root}/stats/mood.png"),
            ("productivity", "Hours of Productivity", True, "4/23/26", f"{git_root}/stats/productivity.png"),
            ("screentime", "Hours of Phone-based Screentime", True, "5/16/26", f"{git_root}/stats/screentime.png"),
        ]]
        failed = False 
        for proc in procs:
            rc = proc.wait()
            if rc != 0:
                print(f"Process {proc.pid} failed with exit code {rc}")
                failed = True
        if failed:
            raise RuntimeError("One or more processes failed") 

    else:
        # Generate a specific calendar. 
        stats = get_stat(args.stat_keyword)
        plot_calendar(
            statcal=stats, 
            title=args.title, 
            yearly=args.yearly, 
            firstday=args.first_day, 
            out_fname=args.out_fname
        )
