"""Top-level pipeline runner: extract text, parse TOC, split articles, validate TOC.
Usage: python -m pipeline.run_pipeline <path-to-pdf>
"""
import sys
from pathlib import Path
from pipeline.extract_text_pdfminer import extract_text_from_pdf
from pipeline.parse_toc import parse_toc
from pipeline.split_articles import split_articles


def run(pdf_path: str):
    out_txt = 'pipeline/extracted_text.txt'
    print('Extracting text...')
    extract_text_from_pdf(pdf_path, out_txt)
    print('Parsing ToC...')
    toc_lines = parse_toc(Path(out_txt).read_text(encoding='utf-8'))
    Path('pipeline/toc_parsed.txt').write_text('\n'.join(toc_lines), encoding='utf-8')
    print(f'Parsed {len(toc_lines)} ToC lines -> pipeline/toc_parsed.txt')
    print('Splitting articles (placeholder)...')
    split_articles(out_txt, 'pipeline/articles')
    print('Done. Articles in pipeline/articles')

if __name__ == '__main__':
    if len(sys.argv) < 2:
        print('Usage: python -m pipeline.run_pipeline <pdf>')
    else:
        run(sys.argv[1])
