"""
Interactively create and acquire stamps.
"""

# Import script from local directory. 
import os 
import sys 

dname = os.path.dirname(__file__)
sys.path.append(dname)

# Import everything. 
import json 
import readline
import subprocess

from create import create_stamp
from datetime import datetime, UTC 
from PIL import Image
from typing import Dict


def get_date_time() -> str:
    """
    Date and time as a string formatted like YYYY-MM-DD@HH-MM. 
    """

    return datetime.now().astimezone().strftime("%Y-%m-%d@%H-%M")


def get_stamps() -> Dict: 
    """
    Returns all stamp JSON objects.
    """

    if os.path.exists("stamps.json"):
        with open("stamps.json", "r") as f:
            all_json = json.load(f) 
    else:
        all_json = []
    return all_json


def add(data: Dict[str, str]): 
    """
    Adds a new stamp to the collection, given the JSON required.
    """

    assert set(data.keys()) == {
        "id", "background", "main-text", "corner-text", "acquired", "condition",
        "rarity", "description", "tags", "date"
    }
    basedir = os.path.dirname(__file__)
    
    # "data" contains a valid JSON in the correct format. First, add the rarity 
    # visual modifiers. 
    rarity = data["rarity"]
    if rarity == "common":
        data["text-fill-color"] = "white"
        data["text-border-color"] = "black"
        data["border-type"] = "square"
        data["border-color"] = "white"
        data["style"] = "bold"
        data["effect"] = "none" 
        data["serifs"] = "false"
    elif rarity == "uncommon":
        data["text-fill-color"] = "lime"
        data["text-border-color"] = "black"
        data["border-type"] = "rounded"
        data["border-color"] = "lime"
        data["style"] = "bold"
        data["effect"] = "none" 
        data["serifs"] = "false"
    elif rarity == "rare":
        data["text-fill-color"] = "cyan"
        data["text-border-color"] = "black"
        data["border-type"] = "ridged"
        data["border-color"] = "cyan"
        data["style"] = "bold"
        data["effect"] = "shimmer" 
        data["serifs"] = "true"
    elif rarity == "super":
        data["text-fill-color"] = "red"
        data["text-border-color"] = "black"
        data["border-type"] = "spiky"
        data["border-color"] = "red"
        data["style"] = "italics-bold"
        data["effect"] = "holographic" 
        data["serifs"] = "true"
    elif rarity == "ultra":
        data["text-fill-color"] = "magenta"
        data["text-border-color"] = "black"
        data["border-type"] = "bubble"
        data["border-color"] = "magenta"
        data["style"] = "italics-bold"
        data["effect"] = "pulse" 
        data["serifs"] = "true"
    else:
        raise ValueError(f"Unknown rarity \"{rarity}\"")

    # Next, copy the background to the small format in the media directory, so 
    # we could make more badges of it in the future. 
    if not os.path.exists(f"{basedir}/media"):
        os.mkdir(f"{basedir}/media")
    with Image.open(data["background"]) as img:
        resized = img.resize((100, 65), resample=Image.Resampling.NEAREST)
        new_path = f"media/{os.path.basename(data['background'])}"
        resized.save(f"{basedir}/{new_path}")
        data["background"] = new_path
        print(f"Resized background saved to \"{basedir}/{new_path}\".")

    # Next, create the stamp from the parameters. Save it to the stamp 
    # directory.
    if not os.path.exists(f"{basedir}/stamps"):
        os.mkdir(f"{basedir}/stamps")
    stamp_fname = create_stamp(
        background_path=data["background"], 
        text=data["main-text"], 
        border_type=data["border-type"], 
        corner_text=data["corner-text"], 
        border_color=data["border-color"], 
        text_fill_color=data["text-fill-color"], 
        text_border_color=data["text-border-color"], 
        style=data["style"], 
        serifs=(data["serifs"] == "true"), 
        gray=(data["acquired"] == "false"), 
        effect=data["effect"]
    )
    ext = stamp_fname[stamp_fname.rindex(".")+1:]
    assert ext in ("jpg", "jpeg", "png", "gif"), f"{ext}, {stamp_fname}"
    new_stamp_fname = f"{basedir}/stamps/{data['id']}.{ext}"
    os.rename(os.path.abspath(stamp_fname), new_stamp_fname)
    data["stamp"] = f"stamps/{data['id']}.{ext}"
    print(f"Stamp image saved to \"{new_stamp_fname}\".")
    
    # Next, add the JSON to the log. If anything exists with the same ID, remove
    # the duplicate.
    all_json = get_stamps()
    all_json = [j for j in all_json if j["id"] != data["id"]]   
    all_json.append(data)
    with open("stamps.json", "w") as f:
        json.dump(all_json, f, indent=4)
    print(f"Stamp index updated at \"stamps.json\"")


def add_interactive():
    """
    Adds a new stamp to the collection.
    """

    # Define the default data that appears in the user-visible file. 
    data = {
        "id": "temp (becomes the file name, no extension)", 
        "background": "/path/to/background.png", 
        "main-text": "Text to\\ndisplay", 
        "corner-text": "Optional text to put in corner", 
        "acquired": "(true, false)", 
        "condition": "Plaintext, the condition for acquiring it", 
        "rarity": "(common, uncommon, rare, super, ultra)", 
        "description": "(If acquired, add description)", 
        "tags": "(research, work, fun, food, travel, experience)"
    }
    keys = set(data.keys())
    
    # Read all existing stamps. 
    if os.path.exists("stamps.json"):
        with open("stamps.json", "r") as f:
            all_json = json.load(f) 
    else:
        all_json = []

    # Create a temp file with each field.
    basedir = os.path.dirname(__file__)
    temp_fname = f"{basedir}/temp.txt"
    with open(temp_fname, "w") as f: 
        json.dump(data, f, indent=4)

    while True:
        # Allow the user to input things via vim.
        subprocess.run(["vim", temp_fname])

        # Check the fields to see if they're correct.
        with open(temp_fname, "r") as f:
            try:
                data = json.load(f)
                loaded_correctly = True
            except: 
                loaded_correctly = False
        
        if not loaded_correctly: 
            input("Could not load file as JSON. Press enter to continue.")
        else:
            current_keys = set(data.keys())
            if current_keys != keys:
                # Flag extra/missing keys.
                for extra_key in current_keys - keys:
                    print(f"Error: extra key: \"{extra_key}\"")
                for missing_key in keys - current_keys:
                    print(f"Error: missing key: \"{missing_key}\"")
                input("Press enter to continue.")
            else:
                # Try to parse everything. Ensure each data type is correct.
                all_correct = True
                if not os.path.exists(data["background"]):
                    print(f"Error: path \"{data['background']}\" missing.")
                    all_correct = False 

                if not all(
                    ch in "abcdefghijklmnopqrstuvwxyz0123456789-_"
                    for ch in data["id"]
                ):
                    print((
                        f"Error: id can only contain lowercase, numbers, or "
                        f"dash/underscore, received \"{data['id']}\"."
                    ))
                    all_correct = False 
                elif any(stamp["id"] == data["id"] for stamp in all_json):
                    print(
                        f"Error: id \"{data['id']}\" has been used before."
                    )
                    all_correct = False

                def check(key, options):
                    if data[key] not in options:
                        print((
                            f"Error: {key} must be in {options}, received "
                            f"\"{data[key]}\"."
                        ))
                        return False
                    return True 
                
                all_correct = check(
                    "acquired", 
                    ["true", "false"]
                ) and all_correct
                all_correct = check(
                    "rarity", 
                    ["common", "uncommon", "rare", "super", "ultra"]
                ) and all_correct
                all_correct = check(
                    "tags", 
                    ["research", "work", "fun", "food", "travel", "experience"]
                ) and all_correct

                # If all_correct is True, exit. Otherwise, re-try. 
                if not all_correct: 
                    input("Press enter to continue.")
                else:
                    break

    # We've obtained the JSON from the interactive routine, pass it to 
    # non-interactive handler. 
    data["date"] = get_date_time()
    add(data)


def acquire_interactive():
    pass


def update_interactive():
    """
    Creates the HTML page for the stamps. The HTML has the following format: 
    1. HTML header, present on all pages on this website.
    2. Introduction describing stamps. 
    3. Demo of the example stamps.
    4. All stamps collected in order.
    5. HTML footer, present on all pages on this website. 
    """
    
    # Create header.
    title = "Stampbook"
    html = f"""
        <!DOCTYPE html>
        <html>
          <head>
            
            <meta charset="UTF-8">
            <meta name="viewport" 
              content="width=device-width, initial-scale=1.0">
            <title>{title}</title>
            <link href="/style-content.css" rel="stylesheet" type="text/css" 
              media="all">
          
          </head>
          <body>
            
            <script> 
              const query_string = window.location.search; 
              const url_params = new URLSearchParams(query_string); 
              if (!url_params.has('contentonly')) {{
                const target = window.location.pathname + window.location.hash;
                const dest = encodeURIComponent(target);
                window.location.replace("/index.html?redirect=" + dest); 
              }}
              window.addEventListener("load", () => {{ 
                requestAnimationFrame(() => {{ 
                  const id = location.hash.slice(1); 
                  const el = document.getElementById(id); 
                  if (el) el.scrollIntoView(); 
                }});
              }});
            </script> 
        
            <div style="width: 100%%; height: 100%%;">
              <div class="main-content">
                <div class="main-section">
    """

    # Add introduction describing stamps. 
    html += """
        <h1>Stampbook</h1>
        <p>Each <i>stamp</i> on this page signifies an high achievement, 
        regular accomplishment, or otherwise fun thing I've done. They can span 
        especially serious things (getting an award, publishing a paper, 
        submitting a patent, etc.) to everyday things (watching a show, visiting 
        a new location, eating a new food, etc.).</p>
    """

    # Add demo of example stamps. The example stamps begin with "example-". 
    stamps = get_stamps() 
    html += (
        "<p><details>"
        "<summary style='padding-left: 20px; padding-bottom: 10px;'>"
        "Example stamps"
        "</summary><p>"
    )
    for example in [s for s in stamps if s["id"].startswith("example-")]:
        html += f"<img src=\"{example['stamp']}\">"
    html += "</p></details></p>"

    # Add all other stamps in order. 
    html += "<hr class=\"divider\"><p>"
    for stamp in [s for s in stamps if not s["id"].startswith("example-")]:
        html += f"<img src=\"{stamp['stamp']}\">"
    html += "</p>"
    
    # Add HTML footer. 
    timestamp = datetime.now(UTC).strftime(
        "Last updated: %B %-d, %Y at %H:%M UTC"
    )
    html += f"""
        </div></div>
        <div class=\"last_updated\">
          <p class=\"last-updated-text\">
            {timestamp}
          </p>
        </div>
        </div></body></html>
    """

    # Write updated index to file.
    basedir = os.path.dirname(__file__)
    with open(f"{basedir}/index.html", "w") as f:
        f.write(html)
    print(f"Outputted to \"{basedir}/index.html\"")


def demo():
    """
    Creates demo stamps. 
    """

    background_path = input("Path to background image: ").strip()
    while not os.path.exists(background_path):
        background_path = input("Does not exist, try again: ").strip()

    # Create each stamp. 
    for acquired in ("true", "false"):
        for rarity in ("common", "uncommon", "rare", "super", "ultra"):
            data = {
                "id": (
                    "example-"
                    f"{'' if acquired == 'true' else 'un'}acquired-"
                    f"{rarity}" 
                ), 
                "background": background_path,
                "main-text": rarity[0].upper() + rarity[1:], 
                "corner-text": "1/1/2026" if rarity == "common" else "", 
                "acquired": acquired, 
                "condition": "Sample condition for acquiring stamp",
                "rarity": rarity, 
                "description": (
                    "Sample description after acquiring stamp"
                    if acquired == "true" else ""
                ), 
                "tags": "research", 
                "date": get_date_time()
            }
            add(data)


if __name__ == "__main__":
    while True:
        print("Input an action:")
        print("  1: add a new stamp") 
        print("  2: acquire an existing stamp")
        print("  3: update the stampbook")
        print("  4: create demo stamps")
        try:
            action = input("> ").strip()
        except (EOFError, KeyboardInterrupt):
            action = ""
    
        if len(action) == 0:
            print("Bye!")
            exit(0)
        elif action == "1":
            add_interactive()
        elif action == "2":
            acquire_interactive()
        elif action == "3": 
            update_interactive()
        elif action == "4":
            demo()
        else:
            print(f"Unrecognized action \"{action}\"")

        print()
