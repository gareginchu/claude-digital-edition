"""Top-level pipeline runner: extract text, parse TOC, split articles, validate TOC.
Usage: python -m pipeline.run_pipeline <path-to-pdf>
"""
import sys
from pathlib import Path
from pipeline.extract_text_pdfminer import extract_text_from_pdf
from pipeline.parse_toc import parse_toc
from pipeline.split_articles import split_articles, split_articles_by_toc


def run(pdf_path: str):
    out_txt = 'pipeline/extracted_text.txt'
    toc_out = 'pipeline/toc_parsed.txt'
    print('Extracting text...')
    extract_text_from_pdf(pdf_path, out_txt)
    print('Parsing ToC...')
    toc_lines = parse_toc(Path(out_txt).read_text(encoding='utf-8'))
    Path(toc_out).write_text('\n'.join(toc_lines), encoding='utf-8')
    print(f'Parsed {len(toc_lines)} ToC lines -> pipeline/toc_parsed.txt')
    print('Splitting articles (ToC-aligned)...')
    try:
        split_articles_by_toc(out_txt, toc_out, 'pipeline/articles')
    except Exception as exc:
        print(f'ToC split failed ({exc}); falling back to heuristic splitter.')
        split_articles(out_txt, 'pipeline/articles')
    print('Done. Articles in pipeline/articles')

if __name__ == '__main__':
    if len(sys.argv) < 2:
        print('Usage: python -m pipeline.run_pipeline <pdf>')
    else:
        run(sys.argv[1])
