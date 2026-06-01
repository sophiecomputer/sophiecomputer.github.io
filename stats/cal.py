"""
Creates a calendar and shades in days of it.
"""

# Load the virtual environment.
import os
import sys
import site

base = os.path.dirname(os.path.abspath(__file__)) + "/../"
venv_site = os.path.join(
    base, 
    ".venv", 
    "lib", 
    f"python{sys.version_info.major}.{sys.version_info.minor}", 
    "site-packages"
)
site.addsitedir(venv_site)


import calendar
import math 
import matplotlib.pyplot as plt
import random
import re 
import argparse 
from collections import defaultdict
from typing import Any, Dict, List, Optional, Tuple 
import datetime 


def config_matplotlib():
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


SINGLE_COLUMN_WIDTH = 3.33  # Inches
DOUBLE_COLUMN_WIDTH = 6.875 

header_color = "#660066" 
shaded_color = "#bd00ff" 


def get_days(
    fname: str, 
    reg: str, 
    almost_reg: str
) -> Tuple[List[re.Match], Optional[List[re.Match]]]: 
    """
    Given a file containing items to match, returns the collection of all 
    matched items in the file. If an "almost-match" is specified, returns that
    too.
    """

    assert os.path.exists(fname), f"\"{fname}\" does not exist." 
    reg = re.compile(reg) 
    almost_reg = re.compile(almost_reg) if almost_reg else None

    matches = []
    almost_matches = [] if almost_reg else None
    with open(fname, "r") as f:
        for line in f: 
            if "none" not in line.lower():
                if mat := reg.match(line):
                    matches.append(mat)
                elif almost_reg and (mat := almost_reg.match(line)):
                    almost_matches.append(mat)
    
    return matches, almost_matches


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
    title: str, 
    yearly: bool, 
    firstday: Tuple[int], 
    fname: str, 
    out_fname: str, 
    value: str
):
    """
    Draws a calendar. "yearly" is True if we plot an entire year or False if we 
    plot a single month. "firstday" is a tuple of (year, month, day), where 
    everything before this day is shaded in gray. "value" must be an enum
    specifier.
    """
    
    assert value in ("none", "counter", "anime", "mood", "hours") 
    first_date = datetime.date(
        year=int(firstday[0]),
        month=int(firstday[1]),
        day=int(firstday[2])
    )

    # Get the content from the file. In each regex, the fields are:
    #   mat[2]: month
    #   mat[3]: day
    #   mat[4]: year
    #   mat[5]: key (optional)
    #   mat[6]: extra text 
    if value == "none":
        reg = r"([\*\s#]*)(\d+)\/(\d+)\/(\d+)()()"
        almost_reg = r".+(\d+)\/(\d+)\/(\d+)"
    elif value == "counter": 
        reg = r"([\*\s#]*)(\d+)\/(\d+)\/(\d+)()()"
        almost_reg = r".+(\d+)\/(\d+)\/(\d+)"
    elif value == "anime": 
        reg = r"([\*\s#]*)(\d+)\/(\d+)\/(\d+) (.+) ([^\s]+)"
        almost_reg = r".+(\d+)\/(\d+)\/(\d+).+"
    elif value == "mood":
        reg = r"([\*\s#]*)(\d+)\/(\d+)\/(\d+) (\d+)()"
        almost_reg = r".+(\d+)\/(\d+)\/(\d+).+"
    elif value == "hours":
        reg = r"([\*\s#]*)(\d+)\/(\d+)\/(\d+) (\d+\.?\d*)()"
        almost_reg = r".+(\d+)\/(\d+)\/(\d+).*"
    else:
        raise ValueError(f"Unknown value type: \"{value}\"")

    matches, almost_matches = get_days(fname, reg, almost_reg)
    if len(almost_matches) > 0:
        print((
            f"Error: there are {len(almost_matches)} lines which almost match "
            "the regex. Adjust them before continuing.\n  " 
            + "\n  ".join(mat[0] for mat in almost_matches)
        ))
        exit(1)

    # Condense the matches into cells. Each cell is characterized by a date 
    # (key), a gradient (percent, float), and text (string).
    raw_cells = defaultdict(list)
    for match in matches:
        month = int(match[2])
        day = int(match[3]) 
        year = int(match[4])
        if year < 2000: year += 2000 
        key = match[5] 
        extra_text = match[6] 
        
        if first_date <= datetime.date(year=year, month=month, day=day): 
            raw_cells[(month, day, year)].append((key, extra_text))

    # Get the max value for the gradient.
    if value in ("counter", "anime"):
        max_values = len(max(raw_cells.values(), key=lambda x: len(x)))
    elif value == "hours":
        max_values = (
            float(max(raw_cells.values(), key=lambda x: float(x[0][0]))[0][0])
        )

    # Create the formatted dictionary. 
    cells = {} 
    for date, values in raw_cells.items():
        # Set gradient. 
        if value == "none":
            gradient = 1.0
        elif value in ("counter", "anime"):
            gradient = math.log(len(values) + 1) / math.log(max_values + 1)
        elif value == "mood":
            gradient = (int(values[0][0]) - 1) / 5.0
        elif value == "hours": 
            gradient = float(values[0][0]) / max_values

        # Set text.
        if value == "none":
            text = "" 
        elif value == "counter" or (value == "anime" and yearly):
            text = str(len(values))
        elif value == "anime": 
            text = ""
            ilen = min(2, len(values))
            for idx, (key, extra) in enumerate(v for v in values[:ilen]):
                text = key if len(key) <= 5 else key[:5] + "..."
                text += "\n" if idx < ilen - 1 else "" 
        elif value in ("mood", "hours"):
            text = str(values[0][0])

        cells[date] = (gradient, text)
    
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
        cellLoc="center"
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


if __name__ == "__main__": 
    parser = argparse.ArgumentParser(
        prog="plot.py", 
        description="Plots data from markdown files"
    )
    parser.add_argument(
        "data_fname", 
        help="Which file holds the data"
    )
    parser.add_argument(
        "--title", 
        help="Base name of the title", 
        default="Calendar"
    )
    parser.add_argument(
        "--out-fname", 
        help="Where to save the file", 
        default="calendar.png"
    )
    parser.add_argument(
        "--value", 
        help="What to put in the calendar slots",
        choices=["none", "counter", "anime", "mood", "hours"], 
        default="none"
    )
    parser.add_argument(
        "--yearly",
        help="If set, makes the calendar a yearly calendar; otherwise, monthly", 
        action="store_true",
        default=False
    )
    args = parser.parse_args()
    
    if not args.out_fname.startswith("/"):
        args.out_fname = f"{base}/{args.out_fname}" 
    if not os.path.exists(args.data_fname):
        args.data_fname = f"{base}/{args.data_fname}" 

    plot_calendar(
        args.title, 
        args.yearly, 
        (2025, 12, 7), 
        args.data_fname, 
        args.out_fname, 
        args.value
    ) 
