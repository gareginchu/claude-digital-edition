"""Batch convert TEI XML files to HTML."""
from pathlib import Path
import subprocess
import sys

def batch_tei_to_html(tei_dir: str, out_dir: str, renderer_script: str):
    Path(out_dir).mkdir(parents=True, exist_ok=True)
    tei_path = Path(tei_dir)
    for tei_file in tei_path.glob('*.xml'):
        out_file = Path(out_dir) / tei_file.with_suffix('.html').name
        cmd = [sys.executable, renderer_script, str(tei_file), str(out_file)]
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode == 0:
            print(f"Converted {tei_file.name} -> {out_file.name}")
        else:
            print(f"Error converting {tei_file.name}: {result.stderr}")

if __name__ == '__main__':
    if len(sys.argv) < 4:
        print("Usage: batch_tei_to_html.py tei_dir output_dir renderer_script")
    else:
        batch_tei_to_html(sys.argv[1], sys.argv[2], sys.argv[3])
