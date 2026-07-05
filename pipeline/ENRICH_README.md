Batch enrich TEI files with named entities and manuscript references.

Usage:
```bash
python pipeline/enrich_tei.py tei/ tei_enriched/
```

This adds a `<standOff>` section to each TEI file with:
- Extracted person names (Armenian names detected via script detection)
- Manuscript references (Matenadaran shelfmarks + foreign ms sigla)
- Entity linking stubs (ready for Wikidata QID population)

Output files can be used to replace originals or serve as enrichment templates for human review.
