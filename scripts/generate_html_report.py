import os
import re

MD_PATH = r"c:\Users\divya\DataDrive\Study\Projects\FlytLabs_MLH\SUBMISSION_REPORT.md"
HTML_PATH = r"c:\Users\divya\DataDrive\Study\Projects\FlytLabs_MLH\SUBMISSION_REPORT.html"

with open(MD_PATH, "r", encoding="utf-8") as f:
    md_content = f.read()

# Simple markdown to styled HTML converter
html_body = []
lines = md_content.split("\n")
in_table = False
table_header = False
in_code = False
code_lines = []

for line in lines:
    if line.startswith("```"):
        if in_code:
            in_code = False
            html_body.append(f"<pre><code>{os.linesep.join(code_lines)}</code></pre>")
            code_lines = []
        else:
            in_code = True
            code_lines = []
        continue
        
    if in_code:
        code_lines.append(line.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;"))
        continue
        
    if line.startswith("|") and line.endswith("|"):
        cells = [c.strip() for c in line.split("|")[1:-1]]
        if all(re.match(r"^:?-+:?$", c) for c in cells):
            table_header = False
            continue
            
        if not in_table:
            in_table = True
            table_header = True
            html_body.append("<div class='table-container'><table>")
            
        if table_header:
            row_html = "".join(f"<th>{c}</th>" for c in cells)
            html_body.append(f"<thead><tr>{row_html}</tr></thead><tbody>")
            table_header = False
        else:
            row_html = "".join(f"<td>{c}</td>" for c in cells)
            html_body.append(f"<tr>{row_html}</tr>")
        continue
    else:
        if in_table:
            in_table = False
            html_body.append("</tbody></table></div>")
            
    if line.startswith("# "):
        html_body.append(f"<h1>{line[2:]}</h1>")
    elif line.startswith("## "):
        html_body.append(f"<h2>{line[3:]}</h2>")
    elif line.startswith("### "):
        html_body.append(f"<h3>{line[4:]}</h3>")
    elif line.startswith("---"):
        html_body.append("<hr class='page-break'/>")
    elif line.startswith("> "):
        html_body.append(f"<blockquote>{line[2:]}</blockquote>")
    elif line.startswith("- "):
        html_body.append(f"<li>{line[2:]}</li>")
    elif line.strip() == "":
        html_body.append("<br/>")
    else:
        # Convert inline markdown
        p = line
        p = re.sub(r"\*\*(.*?)\*\*", r"<strong>\1</strong>", p)
        p = re.sub(r"\*(.*?)\*", r"<em>\1</em>", p)
        p = re.sub(r"`(.*?)`", r"<code>\1</code>", p)
        html_body.append(f"<p>{p}</p>")

if in_table:
    html_body.append("</tbody></table></div>")

full_html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<title>RigSync Final Submission Report - FlytBase MLH Hackathon</title>
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=JetBrains+Mono:wght@400;500&display=swap');
    
    @page {{
        size: A4;
        margin: 1.5cm;
    }}
    
    body {{
        font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
        line-height: 1.5;
        color: #1e293b;
        background-color: #f8fafc;
        margin: 0;
        padding: 40px;
    }}
    
    .document {{
        max-width: 1000px;
        margin: 0 auto;
        background: #ffffff;
        padding: 50px 60px;
        border-radius: 12px;
        box-shadow: 0 4px 20px rgba(0, 0, 0, 0.05);
    }}
    
    h1 {{
        color: #0f172a;
        font-size: 26px;
        font-weight: 700;
        border-bottom: 2px solid #3b82f6;
        padding-bottom: 12px;
        margin-top: 30px;
        margin-bottom: 16px;
    }}
    
    h2 {{
        color: #1e3a8a;
        font-size: 20px;
        font-weight: 600;
        margin-top: 24px;
        margin-bottom: 12px;
    }}
    
    h3 {{
        color: #2563eb;
        font-size: 16px;
        font-weight: 600;
        margin-top: 20px;
        margin-bottom: 8px;
    }}
    
    p, li {{
        font-size: 13.5px;
        color: #334155;
    }}
    
    .table-container {{
        overflow-x: auto;
        margin: 16px 0;
    }}
    
    table {{
        width: 100%;
        border-collapse: collapse;
        font-size: 12px;
        background: #ffffff;
    }}
    
    th, td {{
        border: 1px solid #cbd5e1;
        padding: 7px 10px;
        text-align: left;
    }}
    
    th {{
        background-color: #f1f5f9;
        font-weight: 600;
        color: #0f172a;
    }}
    
    tr:nth-child(even) {{
        background-color: #f8fafc;
    }}
    
    pre {{
        background-color: #0f172a;
        color: #f8fafc;
        padding: 16px;
        border-radius: 8px;
        font-family: 'JetBrains Mono', monospace;
        font-size: 11.5px;
        line-height: 1.4;
        overflow-x: auto;
    }}
    
    code {{
        font-family: 'JetBrains Mono', monospace;
        font-size: 12px;
        background-color: #f1f5f9;
        padding: 2px 5px;
        border-radius: 4px;
        color: #0f172a;
    }}
    
    pre code {{
        background: transparent;
        color: #f8fafc;
        padding: 0;
    }}
    
    blockquote {{
        border-left: 4px solid #3b82f6;
        margin: 14px 0;
        padding: 10px 16px;
        background-color: #eff6ff;
        color: #1e40af;
        font-size: 13px;
        border-radius: 0 6px 6px 0;
    }}
    
    .page-break {{
        border: none;
        border-top: 2px dashed #cbd5e1;
        margin: 35px 0;
    }}
    
    @media print {{
        body {{
            background: #ffffff;
            padding: 0;
        }}
        .document {{
            box-shadow: none;
            padding: 0;
            max-width: 100%;
        }}
        .page-break {{
            page-break-after: always;
            border: none;
            visibility: hidden;
            margin: 0;
        }}
        pre, table {{
            page-break-inside: avoid;
        }}
    }}
</style>
</head>
<body>
<div class="document">
{"".join(html_body)}
</div>
</body>
</html>
"""

with open(HTML_PATH, "w", encoding="utf-8") as f:
    f.write(full_html)

print("Generated HTML report at:", HTML_PATH)
