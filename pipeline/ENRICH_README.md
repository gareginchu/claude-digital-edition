Batch enrich TEI files with named entities and manuscript references.

Usage:
```bash
python pipeline/enrich_tei.py tei/ tei_enriched/
```

Default behavior:
- Enriches only `article_001.xml` through `article_055.xml`.
- Skips `article_056.xml` and non-article TEI files unless explicitly enabled.

Include back matter explicitly:
```bash
python pipeline/enrich_tei.py tei/ tei_enriched/ --include-backmatter
```

Custom article window:
```bash
python pipeline/enrich_tei.py tei/ tei_enriched/ --start-article 1 --end-article 55
```

Optional structural split for back matter source text:
```bash
python pipeline/split_back_matter.py pipeline/articles/article_056.txt pipeline/backmatter/
```

This adds a `<standOff>` section to each TEI file with:
- Extracted person names (Armenian names detected via script detection)
- Manuscript references (Matenadaran shelfmarks + foreign ms sigla)
- Entity linking stubs (ready for Wikidata QID population)

Output files can be used to replace originals or serve as enrichment templates for human review.
