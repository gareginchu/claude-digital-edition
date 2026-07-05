"""Simple ToC parser: find lines that look like TOC entries (title ... page).
This is a heuristic placeholder — replace with project-specific parser.
"""
import re
from pathlib import Path

def parse_toc(text: str):
    toc_lines = []
    for line in text.splitlines():
        if re.search(r"\.{2,}\s*\d+$", line) or re.search(r"\b\d{1,3}$", line):
            toc_lines.append(line.strip())
    return toc_lines

if __name__ == '__main__':
    import sys
    t = Path(sys.argv[1]).read_text(encoding='utf-8')
    for l in parse_toc(t):
        print(l)
