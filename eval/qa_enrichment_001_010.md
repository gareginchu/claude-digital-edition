# Enrichment QA Report: articles 001-010

Date: 2026-07-05
Scope: `tei_enriched/article_001.xml` ... `tei_enriched/article_010.xml`

## Summary

- Completed final QA rerun for articles 001-010 after second-layer filtering and person-shape constraints.
- Improvement: ORG/PLACE leakage is significantly reduced across the batch.
- Improvement: duplicate manuscript refs in article_008 remain resolved (`Bodleian Library` appears once).
- Remaining issue: minor noisy/truncated candidates still appear in article_007 and article_008.
- Note on article_010: this is lexicon-like content (`...ԲԱՌԱՐԱՆ`) and currently yields 0 person entities by design.

## Article Status

| Article | Persons total | Main issue | Status |
|---|---:|---|---|
| article_001 | 10 | Mostly person-like after filter pass | Acceptable with review |
| article_002 | 8 | Mostly plausible person entities | Acceptable with review |
| article_003 | 0 | No extracted entities in this pass | Review manually |
| article_004 | 4 | Mostly canonical historical names | Acceptable with review |
| article_005 | 0 | No person entities extracted | Review manually |
| article_006 | 5 | Improved precision; minor truncation risk remains | Acceptable with review |
| article_007 | 3 | Low recall; one truncated candidate remains | Needs cleanup |
| article_008 | 5 | Much cleaner; one likely non-person/title phrase remains | Needs cleanup |
| article_009 | 3 | Plausible person names only | Acceptable with review |
| article_010 | 0 | Lexicon-style text; no person entities expected in current rules | Acceptable with review |

## Concrete Findings

- First-pass long-sentence false positives remain resolved.
- Previously noisy ORG/PLACE fragments (`Երեւանի Ֆիզիկական`, `Նյու Յորք`, `Արաբերեն Պարսկերեն`) are no longer present in `listPerson`.
- Remaining noisy examples:
   - `Կոստանդին Երզն` (likely truncated)
   - `Դպիր Կոստանդնուպօլսեցի` (title-like phrase)
- `article_008` manuscript refs remain deduplicated (`Bodleian Library`).

## Recommendation Before Batch 011-020

1. Proceed to QA batch 011-020.
2. Keep a targeted cleanup ticket for truncated/title-like candidates (`article_007`, `article_008`) and apply it before any public-facing enrichment release.
3. Treat lexicon-style units (like `article_010`) as a separate enrichment profile where person extraction may legitimately be empty.
