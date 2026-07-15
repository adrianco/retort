#!/usr/bin/env python3
"""Render optimal-blog.md -> a clean, self-contained optimal-blog.html.

Good for Medium import (semantic h1/h2/table/pre) and general viewing (embedded
CSS, light/dark aware, responsive tables). Run via:
    uv run --with markdown python md2html.py <in.md> <out.html>
"""
import re
import sys

import markdown

src, dst = sys.argv[1], sys.argv[2]
text = open(src).read()

# Drop the machine-generation marker comments — invisible in browsers, but noise
# on import. Keep the tables that sit between them.
text = re.sub(r"^<!-- GEN:[^\n]*-->\n?", "", text, flags=re.MULTILINE)

html_body = markdown.markdown(
    text,
    extensions=["tables", "fenced_code", "toc", "sane_lists", "attr_list"],
    output_format="html5",
)

# Pull the <h1> title out for <title>/header.
m = re.search(r"<h1[^>]*>(.*?)</h1>", html_body, re.S)
title = re.sub("<[^>]+>", "", m.group(1)).strip() if m else "The Optimal Stack"

CSS = """
:root { color-scheme: light dark; }
* { box-sizing: border-box; }
body {
  margin: 0; padding: 3rem 1.25rem 5rem;
  font: 18px/1.7 -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
  color: #1a1a1a; background: #fff;
  -webkit-font-smoothing: antialiased;
}
main { max-width: 760px; margin: 0 auto; }
h1, h2, h3 { line-height: 1.25; font-weight: 700; margin: 2.4rem 0 1rem; }
h1 { font-size: 2.3rem; margin-top: 0; letter-spacing: -0.02em; }
h2 { font-size: 1.6rem; padding-top: 1rem; border-top: 1px solid #ececec; }
h3 { font-size: 1.25rem; }
p, li { font-size: 1.06rem; }
a { color: #0b6efd; text-decoration: none; }
a:hover { text-decoration: underline; }
strong { font-weight: 700; }
em { color: #333; }
hr { border: 0; border-top: 1px solid #ececec; margin: 2.5rem 0; }
blockquote {
  margin: 1.5rem 0; padding: 0.6rem 1.2rem; border-left: 4px solid #0b6efd;
  background: #f6f9ff; border-radius: 0 6px 6px 0; color: #24303f;
}
blockquote p { margin: 0.3rem 0; }
code {
  font: 0.86em "SF Mono", "JetBrains Mono", Menlo, Consolas, monospace;
  background: #f2f3f5; padding: 0.12em 0.4em; border-radius: 4px;
}
pre {
  background: #f7f8fa; border: 1px solid #ececec; border-radius: 8px;
  padding: 1rem 1.2rem; overflow-x: auto; line-height: 1.5;
}
pre code { background: none; padding: 0; font-size: 0.9rem; }
.table-wrap { overflow-x: auto; margin: 1.4rem 0; }
table { border-collapse: collapse; width: 100%; font-size: 0.94rem; }
th, td { padding: 0.55rem 0.8rem; border: 1px solid #e6e6e6; text-align: left; }
th { background: #f4f6f8; font-weight: 600; }
tbody tr:nth-child(even) { background: #fafbfc; }
td[align="right"], th[align="right"] { text-align: right; }
.byline { color: #6b7280; font-size: 0.95rem; margin: -0.5rem 0 2rem; }
@media (prefers-color-scheme: dark) {
  body { color: #e6e6e6; background: #0f1115; }
  h2 { border-top-color: #262a31; }
  em { color: #c9c9c9; }
  hr { border-top-color: #262a31; }
  a { color: #63a2ff; }
  blockquote { background: #12203a; border-left-color: #63a2ff; color: #cfe0ff; }
  code { background: #1c2027; }
  pre { background: #14171d; border-color: #262a31; }
  th { background: #1a1e25; }
  th, td { border-color: #2a2f37; }
  tbody tr:nth-child(even) { background: #12151b; }
  .byline { color: #9aa4b2; }
}
"""

# Wrap every table in a horizontally-scrollable div so wide tables never break
# the mobile layout (Medium ignores this, browsers honour it).
html_body = html_body.replace("<table>", '<div class="table-wrap"><table>').replace(
    "</table>", "</table></div>"
)

doc = f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{title}</title>
<style>{CSS}</style>
</head>
<body>
<main>
{html_body}
</main>
</body>
</html>
"""

open(dst, "w").write(doc)
print(f"wrote {dst} ({len(doc):,} bytes)")
