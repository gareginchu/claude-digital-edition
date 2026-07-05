"""Structure-aware TEI chunker for the Chookaszian corpus.

Design constraints (from CLAUDE.md Phase 5):
- Never cross article boundaries.
- Each chunk carries a contextual prefix: article title + section heading.
- Footnotes are attached as metadata to anchor paragraphs, not as separate chunks.
- Chunk size target: ~300-500 tokens (approx 1500-2500 chars for Armenian text).
- Output: list of dicts with 'text', 'article_id', 'title', 'pages', 'chunk_index',
  'footnotes', and 'persons' (from standOff) for downstream indexing.
"""
from pathlib import Path
from typing import List, Dict, Optional
from lxml import etree
import re

NS = {'tei': 'http://www.tei-c.org/ns/1.0'}

# Armenian -> Latin transliteration so English queries can match chunk text
_ARM = {
    'Ա': 'A', 'ա': 'a', 'Բ': 'B', 'բ': 'b', 'Գ': 'G', 'գ': 'g',
    'Դ': 'D', 'դ': 'd', 'Ե': 'Ye', 'ե': 'e', 'Զ': 'Z', 'զ': 'z',
    'Է': 'E', 'է': 'e', 'Ը': 'u', 'ը': 'u', 'Թ': 'Th', 'թ': 'th',
    'Ժ': 'Zh', 'ժ': 'zh', 'Ի': 'I', 'ի': 'i', 'Լ': 'L', 'լ': 'l',
    'Խ': 'Kh', 'խ': 'kh', 'Ծ': 'Ts', 'ծ': 'ts', 'Կ': 'K', 'կ': 'k',
    'Հ': 'H', 'հ': 'h', 'Ձ': 'Dz', 'ձ': 'dz', 'Ղ': 'Gh', 'ղ': 'gh',
    'Ճ': 'Ch', 'ճ': 'ch', 'Մ': 'M', 'մ': 'm', 'Յ': 'Y', 'յ': 'y',
    'Ն': 'N', 'ն': 'n', 'Շ': 'Sh', 'շ': 'sh', 'Ո': 'Vo', 'ո': 'o',
    'Չ': 'Ch', 'չ': 'ch', 'Պ': 'P', 'պ': 'p', 'Ջ': 'J', 'ջ': 'j',
    'Ռ': 'R', 'ռ': 'r', 'Ս': 'S', 'ս': 's', 'Վ': 'V', 'վ': 'v',
    'Տ': 'T', 'տ': 't', 'Ր': 'r', 'ր': 'r', 'Ց': 'Ts', 'ց': 'ts',
    'ու': 'u', 'Ու': 'U', 'Փ': 'Ph', 'փ': 'ph', 'Ք': 'Kh', 'ք': 'kh',
    'Օ': 'O', 'օ': 'o', 'Ֆ': 'F', 'ֆ': 'f', 'և': 'yev',
}


def _translit(s: str) -> str:
    result, i = [], 0
    while i < len(s):
        two = s[i:i+2]
        if two in _ARM:
            result.append(_ARM[two]); i += 2
        elif s[i] in _ARM:
            result.append(_ARM[s[i]]); i += 1
        else:
            result.append(s[i]); i += 1
    return ''.join(result)

CHUNK_TARGET_CHARS = 2000
CHUNK_MAX_CHARS = 3000


def _text(el) -> str:
    """Recursively extract text from an lxml element."""
    return (etree.tostring(el, encoding='unicode', method='text') or '').strip()


def _extract_persons(root) -> List[str]:
    """Return canonical person names from standOff."""
    return [
        pn.text.strip()
        for p in root.findall('.//tei:standOff/tei:listPerson/tei:person', NS)
        if (pn := p.find('tei:persName', NS)) is not None and pn.text
    ]


def chunk_tei_file(tei_path: str) -> List[Dict]:
    """Chunk a single enriched TEI article into context-prefixed segments."""
    tree = etree.parse(tei_path)
    root = tree.getroot()
    article_id = Path(tei_path).stem

    title_el = root.find('.//tei:title', NS)
    title = title_el.text.strip() if title_el is not None and title_el.text else article_id

    source_note = root.find('.//tei:note[@type="source_pages"]', NS)
    pages = source_note.text.strip() if source_note is not None and source_note.text else ''

    persons = _extract_persons(root)

    body = root.find('.//tei:body', NS)
    if body is None:
        return []

    # Collect paragraphs and footnotes
    paragraphs = []
    for p in body.iter('{%s}p' % NS['tei']):
        txt = _text(p)
        note_type = p.get('type', '')
        if not txt or note_type == 'source_pages':
            continue
        paragraphs.append(txt)

    footnotes = [
        _text(n) for n in body.iter('{%s}note' % NS['tei'])
        if n.get('place') == 'bottom' and _text(n)
    ]

    # Group paragraphs into chunks
    chunks: List[Dict] = []
    current_paras: List[str] = []
    current_len = 0
    prefix = f'{title} | pages {pages} | '

    def flush(paras, idx):
        if not paras:
            return
        body_text = '\n\n'.join(paras)
        chunk_text = prefix + body_text
        fn_slice = footnotes[idx * 3: (idx + 1) * 3] if footnotes else []
        if persons:
            chunk_text += '\n\n[Persons: ' + ' '.join(_translit(p) for p in persons) + ']'
        chunks.append({
            'article_id': article_id,
            'chunk_index': idx,
            'title': title,
            'pages': pages,
            'text': chunk_text,
            'char_count': len(chunk_text),
            'footnotes': fn_slice,
            'persons': persons,
        })

    chunk_idx = 0
    for para in paragraphs:
        if current_len + len(para) > CHUNK_MAX_CHARS and current_paras:
            flush(current_paras, chunk_idx)
            chunk_idx += 1
            current_paras = []
            current_len = 0
        current_paras.append(para)
        current_len += len(para)
        if current_len >= CHUNK_TARGET_CHARS:
            flush(current_paras, chunk_idx)
            chunk_idx += 1
            current_paras = []
            current_len = 0

    flush(current_paras, chunk_idx)
    return chunks


def chunk_corpus(tei_enriched_dir: str) -> List[Dict]:
    """Chunk all enriched articles in the corpus."""
    all_chunks = []
    for xml_file in sorted(Path(tei_enriched_dir).glob('article_*.xml')):
        article_chunks = chunk_tei_file(str(xml_file))
        all_chunks.extend(article_chunks)
    return all_chunks


if __name__ == '__main__':
    import json, sys
    if len(sys.argv) < 2:
        print('Usage: chunker.py <tei_enriched_dir> [out.json]')
        sys.exit(1)
    chunks = chunk_corpus(sys.argv[1])
    out = sys.argv[2] if len(sys.argv) > 2 else 'rag/chunks.json'
    Path(out).write_text(json.dumps(chunks, ensure_ascii=False, indent=2), encoding='utf-8')
    print(f'Chunked {len(chunks)} segments from {sys.argv[1]} -> {out}')
