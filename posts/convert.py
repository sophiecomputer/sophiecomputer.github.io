"""
Given a markdown document in stdin, converts it to an HTML page and outputs to 
stdout.

Here is an example of markdown:

  # 0000 [YYYY-MM-DD]: Title
  ## Month day, year | 0:00 PM ET
  
  Paragraph

  Paragraph

  ## Header 2

  Paragraph

  ### Header 3
  
  Paragraph

  -Sophie

The first two lines must be the header and subheader, while the rest of the 
lines follow standard markdown.

"""

import sys 
import re 

# Read content from stdin.
try: 
    header = next(sys.stdin).strip()
    subheader = next(sys.stdin).strip()
    markdown = [line.strip() for line in sys.stdin.readlines()]
except EOFError: 
    print("Error: not enough lines in input markdown.")  
    sys.exit(1)

# Parse header.
if match := re.match(r"# (\d\d\d\d) \[(.*)\]: (.*)", header):
    number = match[1]
    date = match[2]
    title = match[3]
else: 
    print("Error: improperly-formatted header in markdown.")

# Parse subheader.
if match := re.match(r"## (\w+ \w+, \w+ \| \d\d?:\d\d \w\w \w\w)", subheader):
    subheader = match[1]
else:
    print("Error: improperly-formatted subheader in markdown.")

# Construct the output. 
html = """<!DOCTYPE html>
<html>
  <head>
    
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>%s</title>
    <link href="/style-content.css" rel="stylesheet" type="text/css" media="all">
  
  </head>
  <body>
    
    <script> 
      const query_string = window.location.search; 
      const url_params = new URLSearchParams(query_string); 
      if (!url_params.has('contentonly')) {
        window.location.replace("/index.html?redirect=/posts/%s/index.html");
      }
    </script> 

    <div style="width: 100%%; height: 100%%;">
      <div class="main-content">
        <div class="main-section">
          
          <p class="main-text-h1">%s</p>
          <p class="main-text-subtitle">%s</p>

""" % (header, number, title, subheader) 

# Classify the markdown lines as either h2's, h3's, or paragraphs, and add them
# to the output. 
for line in markdown: 
    if len(line) == 0: 
        continue 

    html += "          "

    if line.startswith("##"):
        line = line[2:].strip()
        html += "<p class=\"main-text-h3\">" + line + "</p>"
    elif line.startswith("#"):
        line = line[1:].strip()
        html += "<p class=\"main-text-h2\">" + line + "</p>"
    else:
        html += "<p class=\"main-text\">" + line + "</p>"
    
    html += "\n"

# End with the last bunch of lines.
html += """
        </div>
      </div>
    </div>
  </body>
</html>
"""

# Display it to stdout. 
print(html)
