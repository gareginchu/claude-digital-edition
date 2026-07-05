## CLAUDE Project — Status Summary

**Project:** Digital edition of Babken Chookaszian, *Collected Works* Vol. I  
**Date:** 2026-07-05  
**Status:** ✅ Phase 1–4 complete; ready for review & deployment

### Deliverables

#### 1. **Text Extraction & Structuring** ✅
- PDF text layer extracted via `pdfminer.six`
- ToC parsed (24 entries identified)
- Full text split into 573 articles in `pipeline/articles/`

#### 2. **TEI Encoding** ✅
- 573 TEI P5 XML drafts generated: `tei/article_*.xml`
- Minimal encoding (title, body, placeholder structure)
- Ready for human editorial enrichment (@xml:lang, footnotes, refs)

#### 3. **Web Rendering** ✅
- 573 HTML pages generated: `site/html/article_*.html`
- Astro static site scaffold: `site/` (ready for `npm install && npm run dev`)
- Pre-rendered pages linked in `site/src/components/TeiList.astro`

#### 4. **RAG Indexing** ✅
- RAG index with 1685 text chunks: `rag/index.json`
- Article-level and chunk-level metadata
- Ready for embedding + pgvector integration

#### 5. **IIIF Manifests** ✅
- IIIF v3 Presentation manifest skeleton: `iiif/manifests/manifest.json`
- 24-page canvas structure for plates insert

#### 6. **CI/CD Pipelines** ✅
- `.github/workflows/python-package.yml` — tests + validation
- `.github/workflows/tei-render.yml` — full build on push (TEI → HTML → RAG → IIIF)

### Repository Structure
```
/pipeline/        extraction, splitting, validation scripts
/tei/             573 TEI XML files + corpus
/site/            Astro scaffold + 573 HTML pages
/rag/             RAG index JSON + chunking scripts
/iiif/            IIIF manifests
/eval/            Eval sets (empty, ready for benchmarks)
/rights/          Heirs licence placeholder
```

### Next Steps (Suggested Priority)

1. **Push to remote** (5 min)
   - Provide a GitHub URL or create one
   - Run: `git remote add origin <URL>` && `git push -u origin master`

2. **Refine TEI (human review)** (days → weeks)
   - Review TEI drafts in `tei/` against CLAUDE.md requirements
   - Add proper @xml:lang tags, footnotes, manuscript shelfmarks
   - Link to Wikidata for NER entities

3. **Add embeddings to RAG** (30 min–2 hours)
   - Install `sentence-transformers` + `pgvector`
   - Run BGE-M3 over `rag/index.json` chunks
   - Deploy retrieval API

4. **Deploy static site** (30 min–1 hour)
   - GitHub Pages, Netlify, or custom domain
   - `npm run build` in `site/`

### Key Files to Review
- [CLAUDE.md](CLAUDE.md) — project architecture & ethics
- [README.md](README.md) — project overview
- [requirements.txt](requirements.txt) — Python dependencies
- [site/README.md](site/README.md) — Astro setup

### Questions?
Consult CLAUDE.md for architecture decisions, GOVERNANCE.md (when created) for stewardship.

---
**Project initiated:** 2026-07-05  
**Git commits:** 2 (scaffold + full build)  
**Ready for:** human editorial review + deployment
