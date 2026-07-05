"""Extract text from PDF using pdfminer.six (prefers text layer when present)."""
from pdfminer.high_level import extract_text
from pathlib import Path

def extract_text_from_pdf(pdf_path: str, out_txt: str):
    text = extract_text(pdf_path)
    Path(out_txt).write_text(text, encoding='utf-8')

if __name__ == '__main__':
    import sys
    if len(sys.argv) < 3:
        print('Usage: extract_text_pdfminer.py input.pdf output.txt')
    else:
        extract_text_from_pdf(sys.argv[1], sys.argv[2])
