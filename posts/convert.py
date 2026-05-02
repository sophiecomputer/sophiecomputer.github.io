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
    markdown = [line for line in sys.stdin.readlines()] 
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
          
          <h1>%s</h1>
          <h2>%s</h2>

""" % (header, number, title, subheader) 

# Classify the markdown lines as either h4's, h3's, or paragraphs, and add them
# to the output. While we read code, append it to the code string. 
code = None 
reading_code = False 
for line in markdown:
    if len(line.strip()) == 0: 
        continue

    if not reading_code:
        if "```" in line:
            code = "" 
            reading_code = True
            continue 

        line = line.strip() 

        # Substitute asterisks with italics.
        while mat := re.match(r".*(\*[^\*]+\*).*", line):
            text = mat[1][1:-1]
            line = line[:mat.start(1)] + "<i>" + text + "</i>" + line[mat.end(1):]
        
        # Substitute backticks with code.
        while mat := re.match(r".*(`[^`]+`).*", line):
            text = mat[1][1:-1]
            line = line[:mat.start(1)] + "<code>" + text + "</code>" + line[mat.end(1):]
    
        # Substitute links.
        while mat := re.match(r".*(\[[^\]]+\])(\([^\)]+\)).*", line): 
            text = mat[1][1:-1]
            link = mat[2][1:-1]
            line = line[:mat.start(1)] + f"<a href=\"{link}\">{text}</a>" \
                + line[mat.end(2):]
    
        html += "          "
    
        if line.startswith("###"):
            line = line[3:].strip()
            html += "<h4>" + line + "</h4>"
        elif line.startswith("##"):
            line = line[2:].strip()
            html += "<h3>" + line + "</h3>"
        else:
            html += "<p>" + line + "</p>"
        
        html += "\n"
    
    else:
        if "```" in line:   
            reading_code = False
            html += (
                "<div class=\"code-block\"><pre><code>" 
                + code.rstrip() 
                + "</code></pre></div>\n"
            )
        else:
            code += line.replace("\t", "    ")  


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
