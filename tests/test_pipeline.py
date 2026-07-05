from pipeline.extract_text import extract_text
from pipeline.split_articles import split_articles
from pathlib import Path

def test_extract_and_split(tmp_path):
    pdf = tmp_path / "in.pdf"
    txt = tmp_path / "out.txt"
    pdf.write_text("PDF_PLACEHOLDER")
    extract_text(str(pdf), str(txt))
    assert txt.exists()
    outdir = tmp_path / "articles"
    txt.write_text('part1ARTICLE_BREAKpart2')
    split_articles(str(txt), str(outdir))
    files = list(outdir.glob('article_*.txt'))
    assert len(files) == 2
