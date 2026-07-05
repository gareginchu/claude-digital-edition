# Enrichment QA Report: articles 041-050

Date: 2026-07-05
Scope: tei_enriched_041_050/article_041.xml ... tei_enriched_041_050/article_050.xml

## Summary

- Completed final QA rerun for articles 041-050 after targeted institution/title token tightening.
- Precision is clean in this batch; previously observed false positives were removed.
- Manuscript extraction is quiet in this range (0 ms refs across all files).
- Recall is uneven; multiple files produce zero person entities.

## Article Status

| Article | Persons total | Main issue | Status |
|---|---:|---|---|
| article_041 | 0 | No entities extracted | Review manually |
| article_042 | 0 | No entities extracted | Review manually |
| article_043 | 4 | Plausible person entities; one inflected duplicate | Acceptable with review |
| article_044 | 0 | No entities extracted | Review manually |
| article_045 | 0 | No entities extracted | Review manually |
| article_046 | 2 | Plausible person entities | Acceptable with review |
| article_047 | 10 | Strong recall; plausible historical names | Acceptable with review |
| article_048 | 3 | Plausible person entities | Acceptable with review |
| article_049 | 0 | No entities extracted | Review manually |
| article_050 | 4 | Plausible variants of same person (inflection) | Acceptable with review |

## Concrete Findings

- Removed false positives observed in prior pass: `Ողbергутean Матеan`, `Nor-Джухayi Amenaprkchean`, `Araджнордутean Hakhpat`, etc.
- article_047 contains a diverse high-recall set of 10 plausible historical Armenian persons.
- Inflectional variants (e.g. `Yeghiayis Astvatsaturean Mushegheanch` + `Yeghia Musheghyan`) are expected duplicates that benefit from future deduplication.

## Recommendation Before Batch 051-055

1. Proceed to batch 051-055 QA with current heuristics (done simultaneously).
2. Keep follow-up ticket for inflectional deduplication.
