from datetime import date
import argparse 
import re 
import os 


def goal(papers_file):
    """
    Returns how many papers I should have read by now, and how many ahead 
    (positive) or behind (negative) I am on schedule.
    """

    TOTAL_PAPERS = 300
    
    today = date.today()
    start_of_year = date(today.year, 1, 1)
    end_of_year = date(today.year + 1, 1, 1)
    
    days_elapsed = (today - start_of_year).days
    total_days = (end_of_year - start_of_year).days
    
    papers_by_now = int(round(TOTAL_PAPERS * days_elapsed / total_days))
     
    assert os.path.exists(papers_file), (
        f"Error: file \"{papers_file}\" does not exist." 
    )

    papers_read = 0 
    reg = re.compile(r"\d+/\d+/26, .+") 
    with open(papers_file, "r") as f: 
        for line in f:
            if reg.match(line):
                papers_read += 1
    
    sched = papers_read - papers_by_now
    
    return papers_by_now, sched


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("doc")
    args = parser.parse_args()
    assert os.path.exists(args.doc), f"Error: \"{args.doc}\" does not exist."
    assert args.doc.endswith(".md"), f"Error: \"{args.doc}\" incorrect file type." 
        
    papers_by_now, sched = goal(args.doc) 
    print(f"You should have read {papers_by_now} papers by now.")
    if sched >= 0:
        print(f"You're on schedule! You are {sched} papers ahead.")
    else:
        print(f"You're behind schedule... you are {abs(sched)} papers behind.") 
