# Enrichment QA Report: articles 011-020

Date: 2026-07-05
Scope: tei_enriched_011_020/article_011.xml ... tei_enriched_011_020/article_020.xml

## Summary

- Completed baseline QA for articles 011-020 with the current extractor.
- Precision is mixed:
  - Good/acceptable in article_017.
  - Strong ORG/PLACE/bibliographic leakage in article_013, article_014, article_016, article_020.
- Recall is zero in article_011, article_012, article_015, article_018.
- Manuscript extraction triggered in article_019 with 4 foreign-style matches; these look noisy and need stricter filtering.

## Article Status

| Article | Persons total | Main issue | Status |
|---|---:|---|---|
| article_011 | 0 | No entities extracted | Review manually |
| article_012 | 0 | No entities extracted | Review manually |
| article_013 | 2 | Institutional phrases extracted as persons | Needs cleanup |
| article_014 | 9 | Place/institution phrases mixed with names | Needs cleanup |
| article_015 | 0 | No entities extracted | Review manually |
| article_016 | 9 | Bibliographic/title phrases extracted as persons | Needs cleanup |
| article_017 | 5 | Mostly plausible person names | Acceptable with review |
| article_018 | 0 | No entities extracted | Review manually |
| article_019 | 0 | 4 manuscript refs are likely false positives from generic `f.` patterns | Needs cleanup |
| article_020 | 6 | Institution/truncated phrases in person list | Needs cleanup |

## Concrete Findings

- Example false positives in `listPerson`:
  - `Մաշտոցյան Մատենադարանին`
  - `Իրանի Քաղաքաշինության`
  - `Արևմտյան Իրանի`
  - `Ագաթանգեղոսի Պատմութեան`
  - `Մաշտոցյան Մատենադարան`
- `article_019` manuscript refs include noisy items:
  - `f. Հայ -քրդական վէպ Hay-Kʻrdakan vep`
  - `f. Եղիշէ`
  - `f. Moiseï Horenskiï`
  - `f. Drevnosti vostočnye. 1901`

## Recommendation Before Batch 021-030

1. Tighten person extraction for title/institution patterns:
   - Reject candidates containing tokens like `Մատենադարան`, `Պատմութեան`, and abstract region/institution words.
   - Add a guard against geographic adjectives (for example `Արևմտյան`, `Իրանի`) in person candidates.
2. Tighten foreign manuscript regex:
   - Remove broad `f.`/`fol.` catch-all unless paired with a trusted repository cue (`British Library`, `Bodleian`, `Vatican`, `BNF`).
3. Re-run 011-020 after these fixes, then decide on 021-030.
