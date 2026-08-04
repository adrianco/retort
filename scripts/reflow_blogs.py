#!/usr/bin/env python3
"""Reflow *-blog.md so each paragraph is ONE long line.

WHY: the blogs are published to dev.to, which treats a hard-wrapped source line
as a line break rather than reflowing it — so paragraphs wrapped at ~95 columns
arrive with ragged breaks mid-sentence. Markdown itself is indifferent; the
importer is not. So the published files keep one line per paragraph.

WHAT IS LEFT EXACTLY AS-IS (joining any of these would corrupt the document):
  * fenced code blocks (``` / ~~~) — every line is significant
  * indented code blocks (4+ spaces) inside a paragraph context
  * tables — one row per line IS the syntax
  * headings, horizontal rules, HTML comments (incl. the <!-- GEN:… --> markers
    that `retort report optimal` splices tables into)
  * blank lines — they delimit blocks

WHAT IS JOINED:
  * ordinary prose paragraphs
  * list items, including their wrapped continuation lines (the continuation is
    folded into its own item, NOT into the previous one)
  * blockquotes, per paragraph, preserving the "> " prefix

Idempotent: running it twice changes nothing.

Usage:  python scripts/reflow_blogs.py [--check] [FILE ...]
        --check exits 1 if any file would change (for CI), writing nothing.
"""
from __future__ import annotations

import datetime
import re
import subprocess
import sys
from pathlib import Path

FENCE_RE = re.compile(r"^\s*(```|~~~)")
TABLE_RE = re.compile(r"^\s*\|")
HEADING_RE = re.compile(r"^\s{0,3}#{1,6}\s")
HR_RE = re.compile(r"^\s{0,3}([-*_])\s*(\1\s*){2,}$")
HTML_RE = re.compile(r"^\s*<")
# "- ", "* ", "+ ", "1. ", "1) " — with any leading indent
LIST_RE = re.compile(r"^(\s*)([-*+]|\d+[.)])\s+")
QUOTE_RE = re.compile(r"^(\s*>+\s?)(.*)$")
# Footnote lines start with a superscript marker ("² Fast mode…", "¹² GPT-5.6…").
# They are separate blocks: joining them produced one 2,700-character line of
# every footnote run together.
FOOTNOTE_RE = re.compile(r"^[\u00b9\u00b2\u00b3\u2070-\u209f]+\s")
INDENTED_CODE_RE = re.compile(r"^ {4,}\S")


def _is_block_boundary(line: str) -> bool:
    """A line that must never be joined onto a preceding prose line."""
    return (
        not line.strip()
        or FENCE_RE.match(line)
        or TABLE_RE.match(line)
        or HEADING_RE.match(line)
        or HR_RE.match(line)
        or HTML_RE.match(line)
        or LIST_RE.match(line)
        or FOOTNOTE_RE.match(line)
        or QUOTE_RE.match(line)
        or INDENTED_CODE_RE.match(line)
    )


def reflow(text: str) -> str:
    lines = text.split("\n")
    out: list[str] = []
    i = 0
    in_fence = False
    fence_marker = ""

    while i < len(lines):
        line = lines[i]

        # --- fenced code: copy verbatim until the closing fence ---
        if FENCE_RE.match(line):
            m = FENCE_RE.match(line)
            marker = m.group(1)
            if not in_fence:
                in_fence, fence_marker = True, marker
            elif marker == fence_marker:
                in_fence = False
            out.append(line)
            i += 1
            continue
        if in_fence:
            out.append(line)
            i += 1
            continue

        # --- structural lines pass through untouched ---
        if (not line.strip() or TABLE_RE.match(line) or HEADING_RE.match(line)
                or HR_RE.match(line) or HTML_RE.match(line)
                or INDENTED_CODE_RE.match(line)):
            out.append(line)
            i += 1
            continue

        # --- blockquote: join this quoted paragraph ---
        if QUOTE_RE.match(line):
            prefix = QUOTE_RE.match(line).group(1)
            body = [QUOTE_RE.match(line).group(2).rstrip()]
            i += 1
            while i < len(lines):
                m = QUOTE_RE.match(lines[i])
                if not m:
                    break
                rest = m.group(2)
                # blank quote line, a nested list, heading or table ends the run
                if (not rest.strip() or LIST_RE.match(rest) or TABLE_RE.match(rest)
                        or HEADING_RE.match(rest) or FENCE_RE.match(rest)):
                    break
                body.append(rest.strip())
                i += 1
            joined = " ".join(b for b in body if b)
            out.append(f"{prefix.rstrip()} {joined}" if joined else prefix.rstrip())
            # PRESERVE the ">"-only separator that ended this paragraph. Dropping
            # it let two quoted paragraphs become adjacent, so a second run merged
            # them — the transform has to be idempotent or it silently eats
            # structure every time it is applied.
            if i < len(lines):
                m = QUOTE_RE.match(lines[i])
                if m and not m.group(2).strip():
                    out.append(lines[i].rstrip())
                    i += 1
            continue

        # --- list item or footnote: join its own continuation lines ---
        if LIST_RE.match(line) or FOOTNOTE_RE.match(line):
            body = [line.rstrip()]
            i += 1
            while i < len(lines) and not _is_block_boundary(lines[i]):
                body.append(lines[i].strip())
                i += 1
            out.append(" ".join(x.rstrip() for x in body))
            continue

        # --- ordinary paragraph ---
        body = [line.rstrip()]
        i += 1
        while i < len(lines) and not _is_block_boundary(lines[i]):
            body.append(lines[i].strip())
            i += 1
        out.append(" ".join(x for x in body if x))

    return "\n".join(out)


#: Matches both header styles in use:
#:   *Published 2026-07-30 · updated 2026-08-04 — Adrian Cockcroft*
#:   *Living document — last updated 2026-08-01 (first published 2026-07-14).*
UPDATED_RE = re.compile(r"updated (\d{4}-\d{2}-\d{2})")


def stale_dates(paths: list[Path]) -> list[str]:
    """Blogs edited in the working tree whose `updated` date is not today.

    A published page carrying an old date is quietly wrong in a way no reader can
    detect — the content changed, the byline says it didn't. This is checked
    rather than remembered because it was missed four times in one week: three
    blogs shipped edits while still claiming 2026-07-30.

    Only files that actually DIFFER from HEAD are checked, so re-running the
    check on a clean tree never nags.
    """
    today = datetime.date.today().isoformat()
    stale = []
    for path in paths:
        try:
            changed = subprocess.run(
                ["git", "diff", "--quiet", "HEAD", "--", str(path)],
                capture_output=True, timeout=30,
            ).returncode != 0
        except (subprocess.TimeoutExpired, FileNotFoundError, OSError):
            continue
        if not changed:
            continue
        m = UPDATED_RE.search(path.read_text())
        if not m:
            stale.append(f"{path.name}: edited but has no 'updated <date>' in its header")
        elif m.group(1) != today:
            stale.append(f"{path.name}: edited today but still says updated {m.group(1)}")
    return stale


def main(argv: list[str]) -> int:
    check = "--check" in argv
    args = [a for a in argv if not a.startswith("--")]
    repo = Path(__file__).resolve().parents[1]
    paths = [Path(a) for a in args] or sorted(repo.glob("*-blog.md"))

    changed: list[str] = []
    for path in paths:
        original = path.read_text()
        new = reflow(original)
        # sanity: the transform must not lose content
        for name, pat in (("links", r"\]\("), ("table rows", r"^\s*\|"),
                          ("fences", r"^\s*(```|~~~)"), ("headings", r"^\s{0,3}#{1,6}\s")):
            a = len(re.findall(pat, original, re.M))
            b = len(re.findall(pat, new, re.M))
            if a != b:
                print(f"ABORT {path.name}: {name} changed {a} -> {b}", file=sys.stderr)
                return 2
        if new != original:
            changed.append(path.name)
            if not check:
                path.write_text(new)

    if check:
        if changed:
            print("hard-wrapped paragraphs found in: " + ", ".join(changed))
            print("run: python scripts/reflow_blogs.py")
            return 1
        stale = stale_dates(paths)
        if stale:
            print("blog dates are stale — bump the header before publishing:")
            for s in stale:
                print(f"  {s}")
            return 1
        print("all blogs are one-line-per-paragraph, and edited blogs carry today's date")
        return 0

    print("reflowed: " + (", ".join(changed) if changed else "nothing (already clean)"))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
