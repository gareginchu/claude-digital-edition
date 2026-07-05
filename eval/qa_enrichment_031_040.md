# Enrichment QA Report: articles 031-040

Date: 2026-07-05
Scope: tei_enriched_031_040/article_031.xml ... tei_enriched_031_040/article_040.xml

## Summary

- Completed final QA rerun for articles 031-040 after targeted non-person token tightening.
- Precision improved versus the initial pass:
  - Prior false positives from title/institution/location tokens were removed.
  - Remaining extracted entities are concentrated in article_037 and article_038 and are mostly plausible.
- Manuscript extraction is quiet in this range (0 manuscript refs in all files).
- Recall is low for most files in this batch.

## Article Status

| Article | Persons total | Main issue | Status |
|---|---:|---|---|
| article_031 | 0 | No entities extracted | Review manually |
| article_032 | 0 | No entities extracted after stricter filtering | Review manually |
| article_033 | 0 | No entities extracted after stricter filtering | Review manually |
| article_034 | 0 | No entities extracted | Review manually |
| article_035 | 0 | No entities extracted | Review manually |
| article_036 | 0 | No entities extracted | Review manually |
| article_037 | 10 | Plausible entities with variant/inflected duplicates | Acceptable with review |
| article_038 | 1 | Plausible entity (`Էդուարդ Բրաունի`) | Acceptable with review |
| article_039 | 0 | No entities extracted | Review manually |
| article_040 | 0 | No entities extracted | Review manually |

## Concrete Findings

- Removed previously observed noisy patterns from the first pass in this batch:
  - `Արամ Տեր-Ղեվոնդյան Հայ-արաբական`
  - `Կիլիկեան Բժշկարանի`
  - `Կիլիկեան Ձիամատեանը`
  - `Ղեվոնդյան Հայ`
- article_037 still has expected variant-rich person output (inflectional/orthographic forms).

## Recommendation Before Batch 041-050

1. Proceed to batch 041-050 QA with current heuristics.
2. Keep a follow-up ticket for name-variant consolidation (lemmatization/dedup) in high-density files.
3. Continue tracking low-recall files separately and evaluate whether section-aware extraction is needed.
