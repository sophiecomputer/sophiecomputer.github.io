"""
Interactively create and acquire stamps.
"""

# Import script from local directory. 
import os 
import sys 
dname = os.path.dirname(__file__)
sys.path.append(dname)
parent = os.path.dirname(dname)
sys.path.append(parent)
sys.path.append(f"{parent}/stats")

# Import everything. 
import datetime 
import json 
import readline
import subprocess

from create import create_stamp
from PIL import Image
from stats import get_stats, StatDatabase 
from typing import Dict, List
from util import get_git_root


def get_date_time() -> str:
    """
    Date and time as a string formatted like YYYY-MM-DD@HH-MM. 
    """

    return datetime.datetime.now().astimezone().strftime("%Y-%m-%d@%H-%M")


def parse_date_time(datetime_str: str) -> datetime.datetime:
    """
    Parses the datetime in the format from the other function. 
    """
    
    local_tz = datetime.datetime.now().astimezone().tzinfo
    return (
        datetime.datetime.strptime(datetime_str, "%Y-%m-%d@%H-%M")
        .replace(tzinfo=local_tz)
    ) 


def get_stamps() -> List[Dict]: 
    """
    Returns all stamp JSON objects.
    """
    
    fname = f"{get_git_root()}/stamps/stamps.json"
    if os.path.exists(fname):
        with open(fname, "r") as f:
            all_json = json.load(f) 
    else:
        all_json = []
    return all_json


def can_acquire(
    stats: StatDatabase, 
    stamp: Dict, 
    all_stamps: List[Dict]
) -> bool:
    """
    Returns True if we can acquire this stamp.
    """

    if "eval" in stamp and stamp["eval"] is not None:
        assert "progress" in stamp, stamp.keys() 
        assert "freq" in stamp, stamp.keys()
        
        # Two conditions must be true. (1) The stamp must have its "eval" 
        # condition return true. 
        try:
            eval_result = eval(stamp["eval"])
        except:
            print("Error: we failed to evaluate the following stamp:", stamp) 
            raise 

        if not eval_result:
            return False 

        # And (2), the time since the last acquisition of this stamp must be 
        # greater or equal to "freq". We can find this by searching for all 
        # stamps which have the same parent ID as this, and getting the closest
        # distance in days.
        freq = int(stamp["freq"])
        today = datetime.date.today() 
        for st in all_stamps:
            if (
                "parent" in st and 
                st["parent"] is not None and
                stamp["parent"] == st["parent"]
            ):
                # We share the same parent.
                assert "date" in stamp["date"], stamp.keys()
                try: datetime_obj = parse_date_time(stamp["date"])
                except: raise ValueError(repr(stamp)) 
                
                # How much time passed since then? 
                days_since = (today - datetime_obj).days
                if days_since < freq:
                    return False 
        
        # If we made it here, there were no conflicts and the stamp is able
        # to be acquired. 
        return True 

    else:
        return False


def add(data: Dict[str, str]): 
    """
    Adds a new stamp to the collection, given the JSON required.
    """
    
    # Confirm the keys look correct. 
    assert {
        "id", "parent-id", "background", "main-text", "corner-text", "acquired", 
        "condition", "rarity", "description", "tags", "date", "name"
    } - set(data.keys()) == set(), f"Input missing keys: {data.keys()}"
    if any(k in data.keys() for k in ("eval", "progress", "freq")):
        assert {"eval" ,"progress", "freq"} - set(data.keys()) == set(), (
            f"If any of (eval, progress, freq) are in input, then all must be, "
            f"input = {data.keys()}"
        )

    basedir = f"{get_git_root()}/stamps"
    assert os.path.exists(basedir), basedir
    
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
        
    img_path = data["background"]
    if img_path is None:
        # Use default image.
        default_img_path = f"{basedir}/media/default-background.png"
        assert os.path.exists(default_img_path), default_img_path 
        img_path = default_img_path 
    elif not os.path.exists(img_path):
        img_path = f"{basedir}/{data['background']}"
        if not os.path.exists(img_path):
            raise FileNotFoundError(data['background'])

    with Image.open(img_path) as img:
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
        background_path=f"{basedir}/{data['background']}", 
        text=data["main-text"], 
        border_type=data["border-type"], 
        corner_text=data["corner-text"], 
        border_color=data["border-color"], 
        text_fill_color=data["text-fill-color"], 
        text_border_color=data["text-border-color"], 
        style=data["style"], 
        serifs=(data["serifs"] == "true"), 
        gray=(not data["acquired"]), 
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
    fname = f"{basedir}/stamps.json"
    with open(fname, "w") as f:
        json.dump(all_json, f, indent=4)
    print(f"Stamp index updated at \"{fname}\"")


def add_interactive():
    """
    Adds a new stamp to the collection.
    """

    # Define the default data that appears in the user-visible file. 
    data = {
        "id": "temp (becomes the file name, no extension)", 
        "name": "Short name",
        "parent-id": "ID of parent (for automation, can be null)", 
        "background": "/path/to/background.png", 
        "main-text": "Text to\\ndisplay", 
        "corner-text": "Optional text to put in corner", 
        "acquired": True, 
        "condition": "Plaintext, the condition for acquiring it", 
        "rarity": "(common, uncommon, rare, super, ultra)", 
        "description": "(If acquired, add description)", 
        "eval": "E.g., stats.count('workout', 7) >= 3", 
        "progress": "E.g., str(stats.count('workout', 7)) + '/3'", 
        "freq": "Integer, inclusive, number of days pass after acquire again",
        "tags": "(research, work, fun, food, travel, health, experience)"
    }
    keys = set(data.keys())
    
    # Read all existing stamps. 
    all_json = get_stamps()
    
    # Get the stat files. Some stamps involve automated acquisition conditions,
    # so we'll need to ensure those acquisition conditions are correct.
    stats = get_stats()

    # Create a temp file with each field.
    basedir = f"{get_git_root()}/stamps"
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
                        f"Error: id can only contain lowercase, numbers, "
                        f"or dash/underscore, received \"{data['id']}\"."
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
                    [True, False]
                ) and all_correct
                all_correct = check(
                    "rarity", 
                    ["common", "uncommon", "rare", "super", "ultra"]
                ) and all_correct
                all_correct = check(
                    "tags", 
                    ["research", "work", "fun", "food", "travel", 
                        "health", "experience"]
                ) and all_correct

                try:
                    eval(data["eval"])
                except Exception as ex:
                    print((
                        "Error: evaluating the following code in the "
                        "\"eval\" key raised the following error:"
                    ))
                    print(data["eval"])
                    print(ex) 
                    all_correct = False 

                try:
                    eval(data["progress"])
                except Exception as ex:
                    print((
                        "Error: evaluating the following code in the "
                        "\"progress\" key raised the following error:"
                    ))
                    print(data["progress"])
                    print(ex) 
                    all_correct = False 
                
                if not (
                    (
                        isinstance(data["freq"], str) and
                        data["freq"].isnumeric() and
                        int(data["freq"]) > 0
                    )
                    or 
                    (
                        isinstance(data["freq"], int) and 
                        data["freq"] > 0
                    )
                ):
                    print((
                        f"Error: freq \"{data['freq']}\" must be a "
                        "positive integer greater than zero"
                    ))
                    all_correct = False
                else:
                    if isinstance(data["freq"], str):
                        data["freq"] = int(data["freq"])

                # If all_correct is True, exit. Otherwise, re-try. 
                if not all_correct: 
                    input("Press enter to continue.")
                else:
                    # Before continuing, show what the two eval parts 
                    # actually look like to give the user another chance to
                    # re-try.
                    print(
                        "Result of evaluating eval:", 
                        eval(data["eval"])
                    )
                    print(
                        "Result of evaluating progress:", 
                        eval(data["progress"])
                    )
                    if input(
                        "Does this look correct (y/n): "
                    ).strip().lower() == "y":
                        break 

    # We've obtained the JSON from the interactive routine, pass it to 
    # non-interactive handler. 
    data["date"] = get_date_time()
    add(data)


def acquire(stamp: Dict, new: bool) -> None:
    """
    Acquires the given stamp. If "new" is True, we acquire a *new stamp* while
    keeping the parameter the same. Otherwise, we turn this original into 
    acquired. 
    """
    
    if new: 
        # Create a brand new stamp with this as the parent.
        stamp_copy = { key : value for key, value in stamp.items() }
        
        today = datetime.date.today() 
        s = f"{today.year}{today.month:02}{today.day:02}"

        stamp_copy["parent-id"] = stamp["id"]
        stamp_copy["id"] = f"{stamp['id']}-{s}"
        stamp_copy["acquired"] = True
        add(stamp_copy) 
    else:
        # Adjust the original stamp which we have a reference to. 
        stamp["acquired"] = True
        add(stamp)


def acquire_interactive():
    """
    Attempts to acquire existing stamps, and gives the user a chance to manually
    acquire any.
    """

    # First, check if any can be automatically acquired.
    stamps = get_stamps()
    stats = get_stats()
    acquirable = [] 
    for stamp in stamps:
        if can_acquire(stats, stamp, stamps): 
            print(f"We can acquire {stamp['id']}!") 
            acquirable.append(stamp)

    if len(acquirable) > 0:
        choice = input("Acquire all acquirable stamps (y/n): ").strip().lower()
        while choice not in ["y", "n"]: 
            choice = input("Invalid input, try again: ").strip().lower() 

        if choice == "y":
            for stamp in acquirable:
                # Automatically acquirable stamps likely are templates we can
                # do again in the future. 
                acquire(stamp, new=True)
            stamps = get_stamps()
    else:
        print("No stamps may be automatically acquired")

    choice = input("Acquire any stamps manually (y/n): ").strip().lower()
    while choice not in ["y", "n"]: 
        choice = input("Invalid input, try again: ").strip().lower()

    if choice == "n":
        return 

    print("Stamp IDs:")
    print("- " + "\n- ".join(str(stamp["id"]) for stamp in stamps))
    print()

    while True:
        choice = input("Name of stamp (press enter to leave): ").strip()
        if len(choice) == 0:
            break
        else:
            stamp = next(
                (stamp for stamp in stamps if stamp["id"] == choice), 
                None
            )
            if stamp is None:
                print("No stamp has the name \"{choice}\"")
            else:
                choice = input((
                    "Create a new stamp from this (1), or acquire the existing "
                    "stamp (2)? "
                )).strip()
                while choice not in ["1", "2"]: 
                    choice = input("Invalid input, try again: ").strip()

                new = (choice == "1")  
                acquire(stamp, new) 


def update_interactive():
    """
    Creates the HTML page for the stamps. The HTML has the following format: 
    1. HTML header, present on all pages on this website.
    2. Introduction describing stamps. 
    3. Demo of the example stamps.
    4. View stamp info.
    5. All stamps collected in order.
    6. HTML footer, present on all pages on this website. 
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
              
              async function stamp_clicked(stampid) {{
                  try {{
                      const response = await fetch("stamps.json");
                      if (!response.ok) {{
                          throw new Error(
                            `Failed to load stamps.json: ${{response.status}}`);
                      }}
              
                      const stamps = await response.json();
              
                      const stamp = stamps.find(s => s.id === stampid);
                      if (!stamp) {{
                          throw new Error(`Stamp not found: ${{stampid}}`);
                      }}
              
                      document.getElementById("descriptionP").textContent =
                          stamp.description ?? "";
              
                      document.getElementById("conditionP").textContent =
                          stamp.condition ?? "";
                  }} catch (err) {{
                      console.error(err);
                  }}
              }}
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

    def emit_stamp(stamp):
        """
        Emits the HTML for the given stamp. 
        """

        return (
            "<img "
            f"src=\"{stamp['stamp']}\" "
            f"onclick=\"stamp_clicked('{example['id']}');\">"
        )

    # Add demo of example stamps. The example stamps begin with "example-". 
    stamps = get_stamps() 
    html += (
        "<p><details>"
        "<summary style='padding-left: 20px; padding-bottom: 10px;'>"
        "Example stamps"
        "</summary><p>"
    )
    for example in [s for s in stamps if s["id"].startswith("example-")]:
        html += emit_stamp(example) 
    html += "</p></details></p>"

    # Add section for viewing stamp info. 
    html += """
      <hr class="divider">
      <p><b>Description</b>: <span id="descriptionP">
          Click a stamp to view its description.</span></p>
      <p><b>Acquisition condition</b>: <span id="conditionP">
          Click a stamp to view its acquisition condition.</span></p>
      <hr class="divider">
    """

    # Add all other stamps in order.
    html += "<h3>Acquired</h3><p>"
    for stamp in [
        s for s in stamps 
        if (
            not s["id"].startswith("example-") and 
            s["acquired"] in (True, "true")
        )
    ]:
        html += emit_stamp(stamp) 
    html += "</p><h3>Unacquired</h3><p>"
    for stamp in [
        s for s in stamps 
        if (
            not s["id"].startswith("example-") and 
            s["acquired"] in (False, "false")
        )
    ]:
        html += (
            "<img "
            f"src=\"{stamp['stamp']}\" "
            f"onclick=\"stamp_clicked('{stamp['id']}');\">"
        )
    html += "</p>"
    
    # Add HTML footer. 
    timestamp = datetime.datetime.now(datetime.UTC).strftime(
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
    basedir = f"{get_git_root()}/stamps"
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
    for acquired in (True, False):
        for rarity in ("common", "uncommon", "rare", "super", "ultra"):
            data = {
                "id": (
                    "example-"
                    f"{'' if acquired else 'un'}acquired-"
                    f"{rarity}" 
                ), 
                "background": background_path,
                "main-text": rarity[0].upper() + rarity[1:], 
                "corner-text": "1/1/2026" if rarity == "common" else "", 
                "acquired": acquired, 
                "condition": (
                    f"Condition for rarity = {rarity}, "
                    f"acquired = {acquired}"
                ),
                "rarity": rarity, 
                "description": (
                    f"Description for rarity = {rarity}, "
                    f"acquired = {acquired}"
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
