"""
Converts a markdown file to HTML. There are two conversion modes:

1. Does a direct translation of the markdown to an HTML file.
2. Prepends/appends content related to a certain target format (i.e., blog 
   posts).

The user supplies the path to an *output directory* where the "index.html" 
should be written *alongside* any media file. The input markdown file may 
contain media in the form "![[/path/to/media]]" (relative to the input 
directory). This content is copied to a "media/" directory and the resulting 
"index.html" file includes it.

The markdown may contain special fields in it too. Special fields are identified
by being in the format:

%% name: key=value, key=value, key=value %%

(Spacing can be variable, case doesn't matter, but it must be single-line.) 
These special markdown elements are reduced to something else in the resulting
HTML file. For example, it may be converted into a comment field if "name" is 
"comments" and the two keys are "commentsId" and "minimize". 
"""

import argparse
import os
import re
import shlex 
import shutil 
import sys 

from datetime import datetime, UTC 
from pathlib import Path 
from typing import Optional 


def get_args():
    def valid_md(arg):
        if not os.path.exists(arg):
            raise argparse.ArgumentTypeError(f"Path \"{arg}\" does not exist.") 
        if not arg.endswith(".md"):
            raise argparse.ArgumentTypeError(
                f"Path \"{arg}\" is not a Markdown file.")
        return os.path.abspath(arg)

    args = argparse.ArgumentParser()
    args.add_argument("inputpath", type=valid_md, 
        help="Path to the input \".md\" file")
    args.add_argument("outputpath",
        help="Path to where the output directory should be written")
    args.add_argument("--fmt", default="plain", choices=["plain", "blog"],
        help="The format of the outputted HTML")
    args.add_argument("--title", default="SophieComputer Article", 
        help="The title of the outputted HTML page")
    args.add_argument("--webdomain", default="https://sophie.computer", 
        help="The domain of the website (default = https://sophie.computer")
    args.add_argument("--wikilink-root", default=None,
        help=("The root directory of where Wiki-style links (i.e., "
              "\"![[foo]]\" should search content for)"))
    args.add_argument("--force", action="store_true", 
        help=("If supplied, overwrites the target directory if it exists "
              "without asking user for permission"))
    args.add_argument("--out-name", default="index.html", 
        help="The name of the output index file (default = index.html)")
    args.add_argument("--no-delete", action="store_true", 
        help="If set, does not delete outputpath at beginning") 

    return args.parse_args() 


def find_git_root(path: str):
    """
    Traces upwards from the path until a ".git" directory is found. For example,
    if "foo/bar/baz/qux" is given and "foo/bar/.git" exists, then returns 
    "foo/bar".
    """

    path = Path(path).resolve() 
    
    # If a file was provided, start from its parent directory. 
    current = path if path.is_dir() else path.parent 

    # Trace upwards. 
    while True:
        if (current / ".git").is_dir():
            return str(current) 
        
        if current.parent == current:
            raise FileNotFoundError((
                f"Error: no parent directory from \"{str(path)}\" contains a "
                f"\".git\" directory."
            ))

        current = current.parent 


def find_file(fname: str, root_path: str): 
    """
    Finds the file with the given name starting from the root directory. If 
    multiple files have the name, raise an error. 
    """

    matches = [p for p in Path(root_path).rglob(fname) if p.is_file()]
    if len(matches) == 0:
        raise FileNotFoundError(f"{fname} can't be found under {root_path}") 
    if len(matches) > 1: 
        raise ValueError(
            f"Multiple files with name {fname} found under {root_path}"
        )
    return matches[0] 


def blog_format_start(title: str, relative_index: str):
    """
    The start of the blog format. "relative_index" must be relative to the base
    directory of the website (i.e., it must begin with a "/").
    """

    assert (
        relative_index.startswith("/") and 
        relative_index.endswith(".html")
    ), relative_index

    return f"""
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
                window.location.replace("/index.html?redirect={relative_index}");
              }}
            </script> 
        
            <div style="width: 100%%; height: 100%%;">
              <div class="main-content">
                <div class="main-section">
    """


def blog_format_end():
    timestamp = datetime.now(UTC).strftime(
        "Last updated: %B %-d, %Y at %H:%M UTC"
    )
    return f"""
        </div></div>
        <div class=\"last_updated\">
          <p class=\"last-updated-text\">
            {timestamp}
          </p>
        </div>
        </div></body></html>
    """


def convert(
    input_path: str, 
    output_path: str, 
    out_name: str, 
    title: str, 
    force_overwrite: bool,
    fmt: str,
    domain: str,
    wikilink_root: Optional[str],  
    no_delete: bool
) -> None:
    """
    Converts the input path (a markdown file) to an HTML file at 
    "{output_path}/{out_name}". If the markdown file contains any media, then 
    copies that media to "{output_path}/media/*".

    We can specify a target file format. The format can be either "plain" or 
    "blog".

    "domain" is the domain of the website (i.e., "https://example.com").

    "wikilink_root" is where we search for Wiki-style link content.

    If "no_delete" is set, we do not delete things before we begin. 
    """
    
    assert fmt in ("plain", "blog"), fmt 
    
    # Find where the ".git" root is. We're assuming this blog is represented as
    # a GitHub Pages. 
    git_root = os.path.abspath(find_git_root(os.path.abspath(output_path)))
    
    if not no_delete and os.path.exists(output_path): 
        if not force_overwrite: 
            option = input(
                f"The path \"{output_path}\" already exists. Delete it? (y/N): "
            ).strip().lower() 
            
            if option not in ("y", "yes"):
                print("Exiting.")
                exit(0)
            
        # Delete the path. 
        print(f"Deleting \"{output_path}\"") 
        shutil.rmtree(output_path)
    
    # Make the output directory. 
    if not os.path.exists(output_path):
        os.makedirs(output_path)
    output_fname = f"{output_path}/{out_name}" 

    # The file is created in a streaming fashion.
    with open(input_path, "r") as f_in: 
        with open(output_fname, "w") as f_out:
            # Depending on the target file format, write a prelude to the file.
            if fmt == "plain":
                f_out.write("<html>")
            elif fmt == "blog":
                # The user supplied an "output_path" describing where to write 
                # the file. Turn this into an absolute path. 
                output_path = os.path.abspath(output_path)
                rel_path = output_path[len(git_root):] + f"/{out_name}"
                f_out.write(blog_format_start(title, rel_path))
            else:
                raise ValueError(f"Unknown format \"{fmt}\"") 

            # Some markdown elements extend multiple lines. For example:
            #   - comments ("comment") 
            #   - code blocks ("code_block")
            #   - bulleted lists ("bullet_list") 
            #   - numbered lists ("number_list") 
            # For each of these, we must know if we're currently reading 
            # something that extends multiple lines. For the *first line* that 
            # matches this description, emit the start of the block and the 
            # first line. For the first line that *doesn't* match this format, 
            # emit the end of the block. 
            multiline = None
            
            # Process the file.
            for line in f_in:
                if multiline == "code_block":
                    line = line.rstrip()  # Keep tabs/spaces at front 
                else:
                    line = line.strip()
                
                # Assume the line is to be written as a new paragraph <p>. We
                # do *not* emit this as a new paragraph if the line is anything
                # multiline or if it's a header. 
                is_paragraph = True
                
                # Substitutes horizontal lines.
                if line == "- - -":
                    line = "<hr class=\"divider\">"
                    f_out.write(line);
                    continue
                
                # Replace special comment fields. These are unique markdown 
                # elements with custom behavior.
                if line.startswith("%%"):
                    # This may be either a comment or a special line. Special 
                    # lines must have a new pair of "%%" at the end, while 
                    # comments do not.
                    if line[2:].endswith("%%"):
                        # Special line. The line must be in the format
                        # %% name: key=value, key=value, key=value %%
                        mat = re.fullmatch(
                            r"%%\s*([A-Za-z_][A-Za-z0-9_]*)\s*:\s*(.*?)\s*%%",
                            line
                        )
                        if not mat:
                            raise ValueError(f"Invalid directive: \"{line}\"")

                        name = mat.group(1) 
                        args = mat.group(2)
                        
                        # Parse arguments.
                        pairs = {} 
                        if args:
                            lexer = shlex.shlex(args, posix=True)
                            lexer.whitespace = ","
                            lexer.whitespace_split = True
                            lexer.commenters = ""
                            for item in lexer:
                                item = item.strip()
                                if not item:
                                    continue
                                key, value = item.split("=", 1)
                                pairs[key.strip()] = value.strip()
                    
                        # Match the name.
                        if name == "comments":
                            assert all(
                                key in pairs 
                                for key in ("commentsId", "minimize")
                            ), repr(pairs) 

                            commentsId = pairs["commentsId"]
                            minimize = pairs["minimize"]

                            # Write the output. 
                            divId = f"{commentsId}Comments"
                            f_out.write((
                                f"<div id=\"{divId}\"></div>"
                                "<script type=\"module\">"
                                  "import { initComments } from "
                                  "\"/comments.js\";"
                                  f"initComments(\"{commentsId}\", "
                                  f"document.getElementById(\"{divId}\"), "
                                  f"{minimize});"
                                "</script>"
                            ))

                        else:
                            raise ValueError(f"Unknown name {name}") 
                        continue 
                    else:
                        # Comments (specifically, block comments).
                        assert multiline == "comment" or multiline is None
                        if multiline is None:
                            multiline = "comment"
                        else:
                            multiline = None
                            continue  # Don't emit end of comment 

                # Match code blocks.
                if "```" in line:
                    assert line == "```"  # Nothing else besides ```. 
                    assert multiline == "code_block" or multiline is None
                    if multiline is None:
                        # Emit the beginning of the code block.
                        f_out.write("<div class=\"code-block\"><pre><code>")
                        multiline = "code_block" 
                    else:
                        # Emit the end of the code block.
                        f_out.write("</code></pre></div>")
                 
                # Ignore empty lines and don't emit comments. 
                if len(line) == 0 or multiline == "comment":
                    continue

                # Match bulleted lists. 
                if line.startswith("* ") or line.startswith("- "):
                    assert multiline == "bullet_list" or multiline is None
                    if multiline is None:
                        # Emit the beginning of the bullet list. 
                        f_out.write("<ul>") 
                        multiline = "bullet_list" 
                    
                    # We're currently emitting a bullet list. 
                    line = line[2:]  # Remove "* "
                elif multiline == "bullet_list":
                    # We're not matching a bullet list, but we previously were. 
                    # Emit the end of the bullet list. 
                    f_out.write("</ul>") 
                    multiline = None 
                
                # Match numbered lists.
                if re.match(r"^\d+\. ", line):
                    assert multiline == "number_list" or multiline is None
                    if multiline is None:
                        # Emit the beginning of the number list. 
                        f_out.write("<ol>") 
                        multiline = "number_list" 
                    
                    # We're currently emitting a number list.
                    line = line[line.rindex(" ") + 1:]  # Remove number 
                elif multiline == "number_list":
                    # We're not matching a number list, but we previously were. 
                    # Emit the end of the number list. 
                    f_out.write("</ol>") 
                    multiline = None
                
                # Copy images. Replace the line with an image tag, and copy the 
                # input image to the output. (Assert this is actually an image, 
                # too.)
                if mat := re.match(r"!\[\[([^\]]+)\]\]", line):
                    # This is a Wiki-style link. Search for the file name 
                    # relative to the Wiki-link root.
                    name = mat[1] 
                    assert any(
                        name.endswith(ext) 
                        for ext in (".png", ".jpg", ".jpeg", ".svg")
                    ), name
                    assert "/" not in name, name  # Adjust code to work for this
                    assert wikilink_root is not None
                    path = os.path.abspath(find_file(name, wikilink_root))
                    
                    # Copy file to target directory. 
                    if not os.path.exists(f"{output_path}/media"):
                        os.makedirs(f"{output_path}/media") 
                    dest = f"{output_path}/media/{name}"
                    shutil.copyfile(path, dest)
                    print(f"Copied \"{path}\" to \"{dest}\"")

                    line = (
                        "<center><img "
                        + f"src=\"./media/{name}\" "
                        + "style=\"width: 70%; height: auto;\" "
                        + "class=\"center\"></center>"
                    )
                
                if mat := re.match(r"!\[([^\]]+)\]\(([^\)]+)\)", line):
                    # Assert the content is an image. 
                    alt = mat[1].strip()
                    link = mat[2].strip() 
                    assert any(
                        link.endswith(ext) 
                        for ext in (".png", ".jpg", ".jpeg", ".svg")
                    ), f"\"{alt}\", \"{link}\""

                    # If the link is a web hyperlink (beginning with "http://" 
                    # or "https://"), it does not need to be copied anywhere. 
                    # Otherwise, it must be pointed to a file.
                    if not (
                        link.startswith("http://") or 
                        link.startswith("https://")
                    ):
                        assert os.path.exists(link), link

                        # The file exists, so copy it to the target directory.
                        # Get the base name. 
                        basename = link[link.rfind("/")+1:].lstrip("/")
                        target_name = f"{output_path}/media/{basename}"
                        if not os.path.exists(f"{output_path}/media"):
                            os.makedirs(f"{output_path}/media") 
                        shutil.copyfile(link, f"{output_path}/media/{basename}")
                        print(f"Copied \"{link}\" to \"{target_name}\"")
                        link = f"./media/{basename}"

                    line = (
                        "<center><img " 
                        + f"src=\"{link}\" "
                        + f"alt=\"{alt}\" "
                        + "style=\"width: 70%; height: auto;\" "
                        + "class=\"center\"></center>"
                    )

                # Replace inline markdown elements in the line with their HTML
                # equivalents. Note that markdown elements can be repeated on 
                # the same line (i.e., "hello *sophie* super *computer*" 
                # contains two italics). First, substitute triple asterisks with 
                # bold + italics.
                while mat := re.search(r"\*\*\*([^\*]+)\*\*\*", line):
                    line = (
                        line[:mat.start()]
                        + "<b><i>"
                        + mat[1]
                        + "</i></b>"
                        + line[mat.end():]
                    )
                
                # Substitute double asterisks with bold. 
                while mat := re.search(r"\*\*([^\*]+)\*\*", line):
                    line = (
                        line[:mat.start()]
                        + "<b>"
                        + mat[1]
                        + "</b>"
                        + line[mat.end():]
                    )
                
                # Substitute single asterisks with italics. 
                while mat := re.search(r"\*([^\*]+)\*", line):
                    line = (
                        line[:mat.start()]
                        + "<i>"
                        + mat[1]
                        + "</i>"
                        + line[mat.end():]
                    )

                # Substitute backticks with inline code. 
                while mat := re.search(r"`([^`]+)`", line):
                    line = (
                        line[:mat.start()]
                        + "<code>"
                        + mat[1]
                        + "</code>"
                        + line[mat.end():]
                    )

                # Substitute links.
                pattern = (
                    r"\[((?:[^\[\]\\]|\\.|\[(?:[^\[\]\\]|\\.)*\])*)\]"
                    r"\(((?:[^()\\]|\\.|\((?:[^()\\]|\\.)*\))*)\)"
                )
                while mat := re.search(pattern, line): 
                    link = mat[2] 
                    text = mat[1] 
                    
                    # If this is in "blog" format, and if this is not a URL, 
                    # then change the content; otherwise, open in a new tab.
                    if (
                        fmt == "blog" and not (
                            link.startswith("http://") or 
                            link.startswith("https://")
                        )
                    ):
                        # Assuming this is a link relative to the root of the 
                        # website. Assert we can actually find it.
                        link = "/" + link.lstrip("/")
                        web_path = git_root + link
                        assert os.path.exists(web_path), web_path
                        assert link.endswith(".html"), link 

                        line = (
                            line[:mat.start()]
                            + f"<a href=\"{link}?contentonly\" "
                            + f"onclick=\"return window.top.change_me({link}, "
                            + "false);\">"
                            + text
                            + "</a>"
                            + line[mat.end():]
                        )
                    else:
                        line = (
                            line[:mat.start()]
                            + f"<a href=\"{link}\" target=\"_blank\">{text}</a>"
                            + line[mat.end():]
                        )
                
                # Next, modify markdown elements that change the behavior of the
                # entire line. These include bullet/number lists and headers. 
                # Modify the line to include these.
                if multiline in ("bullet_list", "number_list"):
                    line = f"<li>{line}</li>"
                
                headers = {
                    "#####": "h5", 
                    "####" : "h4", 
                    "###"  : "h3", 
                    "##"   : "h2", 
                    "#"    : "h1"
                }
                for header, html in headers.items():
                    if line.startswith(header): 
                        line = (
                            f"<{html}>"
                            + line[len(header):].lstrip()
                            + f"</{html}>"
                        )
                        is_paragraph = False 
                        break 
                
                # Do we write this as a paragraph <p>?
                if is_paragraph and multiline is None: 
                    line = f"<p>{line}</p>" 

                # Write the final line.
                f_out.write(line) 
            
            # Depending on the target file format, write an ending to the file.
            if fmt == "plain":
                f_out.write("</html>")
            elif fmt == "blog":
                f_out.write(blog_format_end())
            else:
                raise ValueError(f"Unknown format \"{fmt}\"") 
    
    print(f"HTML output written to \"{output_fname}\"") 


if __name__ == "__main__":
    args = get_args() 
    convert(
        input_path=args.inputpath, 
        output_path=args.outputpath,
        out_name=args.out_name, 
        title=args.title, 
        force_overwrite=args.force, 
        fmt=args.fmt,
        domain=args.webdomain,
        wikilink_root=args.wikilink_root, 
        no_delete=args.no_delete 
    )
