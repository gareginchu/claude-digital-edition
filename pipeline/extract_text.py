"""Extract text from PDF using pdfminer or external tool; placeholder."""

from pathlib import Path

def extract_text(pdf_path: str, out_txt: str):
    p = Path(out_txt)
    p.write_text(f"Placeholder extracted text from {pdf_path}\n")

if __name__ == "__main__":
    import sys
    if len(sys.argv) < 3:
        print("Usage: extract_text.py input.pdf output.txt")
    else:
        extract_text(sys.argv[1], sys.argv[2])
