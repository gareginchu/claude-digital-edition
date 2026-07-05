# Enrichment QA Report: articles 051-055

Date: 2026-07-05
Scope: tei_enriched_051_055/article_051.xml ... tei_enriched_051_055/article_055.xml
Note: This is the final article batch (articles 001-055 total scope).

## Summary

- Completed QA for the final article batch 051-055.
- Precision is mostly acceptable; one residual mixed-script artefact in article_054 noted below.
- article_054 has a correctly extracted manuscript ref: `Bodleian Library` (1 ms ref).
- Strong recall in articles 053, 054, 055 (10, 8, 10 persons respectively).

## Article Status

| Article | Persons total | MS refs | Main issue | Status |
|---|---:|---:|---|---|
| article_051 | 0 | 0 | No person entities after filtering institution names | Acceptable with review |
| article_052 | 2 | 0 | Plausible person entities | Acceptable with review |
| article_053 | 10 | 0 | Plausible historical names and scholars | Acceptable with review |
| article_054 | 8 | 1 | One mixed-script artefact (`Meghedi Yaroutean`) present | Needs cleanup |
| article_055 | 10 | 0 | Plausible historical and scholarly person names | Acceptable with review |

## Concrete Findings

- article_051: Previously noisy `Tagharan Oxfordi Bodleyan` institution phrase removed.
- article_053: Strong recall; all 10 entries are recognisable scholars/poets.
- article_054: `Meghedi Yaroutean` (Melody of the Resurrection) is a bibliographic title, not a person. This is also a mixed-script token (Armenian + Cyrillic characters from the original PDF extraction), so it requires both a filter fix and a pipeline-level encoding investigation.
- article_054: `Bodleian Library` correctly appears as a manuscript reference (1 ms ref).
- article_055: `Sirarpi Ter-Nersessian` and other prominent scholars correctly extracted.

## Known Issues

- article_054 mixed-script token: `Meghedi Yaroutean` appears due to PDF extraction producing Armenian + Cyrillic character mixtures. This is a pipeline encoding issue separate from the NER filter; tracked for Phase 1 QA investigation.

## Recommendation

1. Full enrichment sweep is complete for articles 001-055.
2. Immediate actions:
   - Investigate mixed-script characters in article_054 at extraction level.
   - Apply inflectional deduplication pass for all batches before public site launch.
3. Enrichment baseline is now ready for a final full-corpus rerun from tei → tei_enriched (single unified output folder) with the current tuned pipeline.
