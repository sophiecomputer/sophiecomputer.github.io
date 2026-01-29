"""
This script automatically updates the website with a new calendar image, 
counters, and log of papers read.
"""


import sys 
import os 
import re 
import subprocess 
from datetime import datetime, timezone 


# Confirm everything exists.
paper_log = "/home/sophie/desktop/data/other/documents/sophie/1-Logs/Papers.md"
cal_script = "/home/sophie/desktop/data/other/documents/sophie/1-Logs/cal.py"
goal_script = "/home/sophie/desktop/data/other/documents/sophie/1-Logs/goal.py"
target_file = __file__[:__file__.rfind("/")] + "/index.html"
out_image = __file__[:__file__.rfind("/")] + "/cal.png"
thumbnail_file = __file__[:__file__.rfind("/")] + "/thumbnail.png"

assert os.path.exists(paper_log), (
    f"Error: paper log doesn't exist at \"{paper_log}\"."
)
assert os.path.exists(cal_script), (
    f"Error: calendar script doesn't exist at \"{cal_script}\"."
)
assert os.path.exists(goal_script), (
    f"Error: goal script doesn't exist at \"{goal_script}\"."
)
assert os.path.exists(target_file), (
    f"Error: target index file does not exist at \"{target_file}\"."
)
assert os.path.exists(out_image), (
    f"Error: output image file should be overwritten, though it currently "
    f"doesn't exist at \"{out_image}\"."
)
assert os.path.exists(thumbnail_file), (
    f"Error: output thumbnail file should be overwritten, though it currently "
    f"doesn't exist at \"{thumbnail_file}\"."
)

sys.path.append(cal_script[:cal_script.rfind("/")])
sys.path.append(goal_script[:goal_script.rfind("/")])
from goal import goal
from cal import plot_calendar 

# Read the log and get the necessary info for each paper.
paper_reg = re.compile(r"(\d+/\d+/\d+), \"(.+),?\" (.+) \[link\]\((.+)\)")
almost_reg = re.compile(r"\d")
warnings = [] 
data = [] 
with open(paper_log, "r") as f:
    for line in f:
        line = line.strip() 
        if mat := paper_reg.match(line):
            date = mat[1] 
            title = mat[2].rstrip(",") 
            other = [mat[i] for i in range(3, len(mat.groups()))]
            link = mat[len(mat.groups())] 
            
            data.append((date, title, link, other))
        
        elif len(line) > 0 and line[0].isnumeric():
            warnings.append(line)

for line in warnings:
    print((
        f"Warning: line \"{line}\" starts with a number but was not "
        "matched correctly." 
    ))
if len(warnings) > 0:
    print("Quitting due to possible errors.") 
    exit(1)

# Construct an HTML table from these lines.
html_table = "<table>\n"
for date, title, link, other in data:
    link_str = f"<a href=\"{link}\" target=\"_parent\">Link</a>"
    other_str = ",".join(other).rstrip(",")
    html_table += (
        "  <tr>"
        f"<td>{date}</td>"
        f"<td>{title}</td>"
        f"<td>{link_str}</td>"
        f"<td>{other_str}</td>"
        "</tr>\n"
    )
html_table += "</table>"

# Last updated time.
now = datetime.now(timezone.utc) 
last_updated_time = now.strftime("%B %d, %Y at %H:%M %Z")
current_date_time = now.strftime("%B %d, %Y")
last_updated_text = (
    "<div class=\"last-updated\">\n" 
    "  <p class=\"last-updated-text\">\n" 
    f"    Last updated: {last_updated_time}.\n"
    "  </p>\n"
    "</div>\n"
)

# Get how many papers are remaining.
papers_by_now, sched = goal()
papers_read_text = (
    f"I have read <b>{str(papers_by_now + sched)} papers</b> this year"
)
papers_by_now_text = (
    f"exactly on schedule" if sched == 0 else 
    f"{sched} papers ahead of schedule" if sched > 0 else 
    f"{abs(sched)} papers behind schedule"
)
summary_text = (
    "<p>This is where I log the papers I've read this year. My goal for 2026 is "
    "to read 300 papers. By the time this document was last updated "
    f"(<b>{current_date_time}</b>), {papers_read_text}. I should have read "
    f"<b>{str(papers_by_now)} papers</b> by this time, meaning I am "
    f"<b>{papers_by_now_text}</b>.</p>"
)

# Generate the calendar.
plot_calendar(
    title="Papers", 
    firstday=(2025, 12, 7), 
    fname=paper_log, 
    out_fname=out_image, 
    value="counter"
)

# Place this table and text into the HTML document between the parts labeled 
# "<paper_table>" + "</paper_table>" or "<summary_text>" + "</summary_text>" or 
# "<last_updated_text> + </last_updated_text>". 
with open(target_file, "r") as f_in:
    with open("temp.html", "w") as f_out:
        reading_summary_text = False
        reading_paper_table = False 
        reading_last_updated_text = False 
        for line in f_in: 
            if "<summary_text>" in line:
                assert not reading_summary_text
                reading_summary_text = True
                f_out.write(line) 
            elif "</summary_text>" in line:
                assert reading_summary_text
                reading_summary_text = False 
                f_out.write(summary_text)
                f_out.write("\n")
                f_out.write(line) 
            elif "<paper_table>" in line:
                assert not reading_paper_table 
                reading_paper_table = True
                f_out.write(line) 
            elif "</paper_table>" in line:
                assert reading_paper_table 
                reading_paper_table = False
                f_out.write(html_table)
                f_out.write("\n")
                f_out.write(line) 
            elif "<last_updated_text>" in line:
                assert not reading_last_updated_text 
                reading_last_updated_text = True
                f_out.write(line) 
            elif "</last_updated_text>" in line:
                assert reading_last_updated_text 
                reading_last_updated_text = False
                f_out.write(last_updated_text)
                f_out.write("\n")
                f_out.write(line) 
            elif (
                not reading_summary_text 
                and not reading_paper_table
                and not reading_last_updated_text
            ):
                f_out.write(line)

assert not reading_summary_text
assert not reading_paper_table
assert not reading_last_updated_text

# Replace file and push.
def run_cmd(cmd):
    cwd = __file__[:__file__.rfind("/")]
    print(" ".join(cmd))
    proc = subprocess.run(
        cmd, 
        cwd=cwd, 
        capture_output=True, 
        text=True
    )
    assert proc.returncode == 0, (
        f"Error in running command.\n{proc.stdout}\n{proc.stderr}"
    )

os.rename("temp.html", target_file)
run_cmd(["magick", out_image, "-resize", "1200x627", "-background", "white",
    "-gravity", "center", "-extent", "1200x627", thumbnail_file])
run_cmd(["git", "add", target_file])
run_cmd(["git", "add", out_image]) 
run_cmd(["git", "add", thumbnail_file]) 
run_cmd(["git", "commit", "-m", 
    f"(Automated) updated paper log: {current_date_time}"])
run_cmd(["git", "push"]) 
