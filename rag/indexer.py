"""Indexer placeholder that writes out JSON metadata for chunks."""
import json
from pathlib import Path

def write_index(chunks, out_path):
    Path(out_path).write_text(json.dumps({'chunks': chunks}, ensure_ascii=False, indent=2))
