# Enrichment QA Report: articles 021-030

Date: 2026-07-05
Scope: tei_enriched_021_030/article_021.xml ... tei_enriched_021_030/article_030.xml

## Summary

- Completed QA rerun for articles 021-030 with current tuned rules.
- Precision is strong in this batch; major ORG/PLACE false positives were not observed after the latest stopword update.
- Manuscript extraction is quiet in this range (0 manuscript refs across all 10 files).
- Recall is uneven, with multiple files producing zero person entities.

## Article Status

| Article | Persons total | Main issue | Status |
|---|---:|---|---|
| article_021 | 0 | No entities extracted | Review manually |
| article_022 | 10 | Plausible historical/person entities; inflected duplicates present | Acceptable with review |
| article_023 | 2 | Plausible person entities | Acceptable with review |
| article_024 | 1 | Plausible person entity | Acceptable with review |
| article_025 | 3 | Plausible person entities | Acceptable with review |
| article_026 | 0 | No entities extracted | Review manually |
| article_027 | 0 | No entities extracted | Review manually |
| article_028 | 0 | No entities extracted | Review manually |
| article_029 | 0 | No entities extracted | Review manually |
| article_030 | 1 | Plausible person entity | Acceptable with review |

## Concrete Findings

- The prior obvious false positive in this range (`Սակայն Պահլավունի`) is removed.
- High-frequency entity variants are mostly inflectional duplicates (for example `Կոստանդին Երզնկացի`, `Կոստանդին Երզնկացու`).
- No noisy foreign manuscript references appear in this batch.

## Recommendation Before Batch 031-040

1. Proceed to batch 031-040 QA with the current heuristics.
2. Open a follow-up normalization ticket to collapse inflectional name variants for better `listPerson` dedup quality.
3. Track low-recall files separately and decide whether they need section-aware or genre-aware extraction profiles.
