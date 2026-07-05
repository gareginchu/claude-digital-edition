# Enrichment QA Report: articles 001-010

Date: 2026-07-05
Scope: `tei_enriched/article_001.xml` ... `tei_enriched/article_010.xml`

## Summary

- Completed second-pass QA for articles 001-010 after extractor tightening.
- Improvement: long prose chunks are largely removed from `listPerson`.
- Improvement: duplicate manuscript refs in article_008 were reduced (`Bodleian Library` now appears once).
- Remaining issue: `listPerson` still includes organizations/places and non-person collocations.
- Third run (second-layer filter) result:
   - Better precision in `article_001` and `article_009`.
   - Remaining mixed-person noise in `article_002`, `article_004`, `article_005`, `article_008`.
   - Recall regression in `article_010` (0 extracted names).

## Article Status

| Article | Persons total | Main issue | Status |
|---|---:|---|---|
| article_001 | 10 | Mostly person-like after filter pass | Acceptable with review |
| article_002 | 10 | Includes place/institution fragments (`Երեւանի Ֆիզիկական`) | Needs cleanup |
| article_003 | 0 | No extracted entities | Review manually |
| article_004 | 10 | Some non-person lexicographic entries remain | Needs cleanup |
| article_005 | 9 | Religious terms/non-person collocations included | Needs cleanup |
| article_006 | 10 | Bibliographic tokens mixed with names | Minor cleanup |
| article_007 | 4 | Low recall + noisy token (`Չինումաչինայ Եւ`) | Needs cleanup |
| article_008 | 10 | Better; still includes truncated/non-person entries | Needs cleanup |
| article_009 | 4 | Mostly plausible person names | Acceptable with review |
| article_010 | 0 | Recall failure in dictionary-style text | Needs cleanup |

## Concrete Findings

- First-pass long-sentence false positives were substantially reduced.
- Current false positives are mostly entity-type errors (ORG/PLACE treated as PERSON).
- Remaining noisy examples:
   - `Հայաստանի Ազգային Գրադարանի`
   - `Երեւանի Ֆիզիկական`
   - `Միջնադարյան Հայաստանի`
   - `Նյու Յորք`
   - `Արաբերեն Պարսկերեն`
- `article_008` manuscript refs no longer duplicate `Bodleian Library`.

## Recommendation Before Batch 011-020

1. Add PERSON/ORG/PLACE disambiguation guard in `pipeline/enrich_tei.py`:
   - Reject candidates whose trailing token is in a non-person stoplist (for example `Գրադարանի`, `Հայաստանի`, `Երևանի`).
   - Reject known toponym bigrams (for example `Նյու Յորք`).
2. Improve recall for article_010 with a dedicated dictionary-name strategy:
   - Parse person names from known bibliographic labels and parenthetical author sections.
   - Keep strict ORG/PLACE stoplists to avoid precision collapse.
3. Re-run enrichment for 001-010 and repeat QA before moving to 011-020.
