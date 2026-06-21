"""
Interactively create and acquire stamps.
"""

# Import script from local directory. 
import os 
import sys 

dname = os.path.dirname(__file__)
sys.path.append(dname)

# Import everything. 
import readline

from create import create_stamp
from PIL import Image


def add_interactive():
    """
    Adds a new stamp to the collection.
    """

    background_path = input("Path to background file: ").strip()
    while not os.path.exists(background_path):
        background_path = input(
            f"Path \"{background_path}\" does not exist, try again: "
        ).strip()

    text = input("Main text (use \\n for newlines): ").strip()
    corner_text = input("Corner text (use \\n for newlines): ").strip()
    border_color = input("Border color (e.g., white): ").strip() 
    text_fill_color = input("Text fill color (e.g., white): ").strip() 
    text_border_color = input("Text border color (e.g., black): ").strip()
    
    style = input(
        "Text style (normal, italics, bold, or italics-bold): "
    ).strip()
    while style not in ("normal", "italics", "bold", "italics-bold"):
        style = input(f"Style \"{style}\" invalid, try again: ").strip()
    
    serifs = input("Should the font have serifs (y/n): ").strip().lower()
    while serifs not in ("y", "yes", "n", "no"):
        serifs = input(
            f"Invalid option \"{serifs}\", try again: "
        ).strip().lower()
    serifs = serifs == "y" or serifs == "yes"

    condition = input("Acquisition condition (plaintext, short): ")


def acquire_interactive():
    pass


def update_interactive():
    pass


if __name__ == "__main__":
    while True:
        print("Input an action:")
        print("  1: add a new stamp") 
        print("  2: acquire an existing stamp")
        print("  3: update the stampbook")
        action = input("> ").strip()

        if len(action) == 0:
            print("Bye!")
            exit(0)
        elif action == "1":
            add()
        elif action == "2":
            acquire()
        elif action == "3": 
            update()
        else:
            print(f"Unrecognized action \"{action}\"")

        print()
