"""Validate extracted ToC against printed ToC (placeholder).
"""
from pathlib import Path

def validate_toc(extracted_toc: str, printed_toc: str) -> bool:
    e = Path(extracted_toc).read_text(encoding='utf-8').strip()
    p = Path(printed_toc).read_text(encoding='utf-8').strip()
    return e == p

if __name__ == "__main__":
    import sys
    ok = validate_toc(sys.argv[1], sys.argv[2])
    print("Match" if ok else "Mismatch")
