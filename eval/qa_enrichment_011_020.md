# Enrichment QA Report: articles 011-020

Date: 2026-07-05
Scope: tei_enriched_011_020/article_011.xml ... tei_enriched_011_020/article_020.xml

## Summary

- Completed post-fix QA rerun for articles 011-020 after tighter person and manuscript filters.
- Precision improved substantially:
  - Institution/place leakage from the baseline pass is largely removed.
  - article_020 no longer includes truncated `Մատենա...` fragment.
- Manuscript noise in article_019 is fully removed (now 0 manuscript refs).
- Recall remains zero in article_011, article_012, article_013, article_015, article_018, article_019.

## Article Status

| Article | Persons total | Main issue | Status |
|---|---:|---|---|
| article_011 | 0 | No entities extracted | Review manually |
| article_012 | 0 | No entities extracted | Review manually |
| article_013 | 0 | No person entities after strict filtering | Review manually |
| article_014 | 7 | Mostly plausible person entities | Acceptable with review |
| article_015 | 0 | No entities extracted | Review manually |
| article_016 | 3 | Mostly plausible person entities | Acceptable with review |
| article_017 | 5 | Mostly plausible person names | Acceptable with review |
| article_018 | 0 | No entities extracted | Review manually |
| article_019 | 0 | No entities extracted; manuscript noise removed | Acceptable with review |
| article_020 | 4 | Cleaner person list after institution-fragment filter | Acceptable with review |

## Concrete Findings

- Baseline false positives such as `Մաշտոցյան Մատենադարանին`, `Իրանի Քաղաքաշինության`, and `Արևմտյան Իրանի` are no longer present.
- `article_019` no longer produces noisy `f.`-style foreign manuscript refs.
- Current person samples are largely historical names and author-like entities.

## Recommendation Before Batch 021-030

1. Proceed to batch 021-030 QA with current heuristics.
2. Keep a follow-up ticket for low-recall files in this batch (011, 012, 013, 015, 018, 019) and evaluate whether they need a separate enrichment profile.
3. Continue manual spot review for borderline historical/title patterns (for example `Արշակունի Արտաւանին`).
