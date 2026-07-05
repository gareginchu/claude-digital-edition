# CLAUDE.md — Digital Edition of Babken Chookaszian, *Collected Works* (Երկերի ժողովածու)

Technical specification for building a digital scholarly edition + public web presentation of the collected articles of Babken Chookaszian (Բաբկէն Չուգասզեան, 1923 Tabriz – 5 Nov 1997 Yerevan), philologist-orientalist, Matenadaran deputy director 1965–1994. Grounded in the intelligence report `AI-Philological-Heritage-Intelligence-Report.md` (Jul 2026). Read that report before making architectural changes.

## Project overview

**Source:** `Babken_Chookaszian_Vol_I.pdf` — 573 pp., Yerevan 2022/2023 second expanded edition (550 pp. + 24-pp. plates insert). **The PDF has a full digital text layer — this is NOT an OCR project.** The work is: extraction → structure recovery → TEI encoding → enrichment → static publication → citation-grounded retrieval.

**Languages:** Eastern Armenian in BOTH classical (Mesropian) and reformed orthography, Russian, French, English, romanized Classical Armenian (Grabar) with diacritics (ʻ ō ē š č ł), Grabar in Armenian script. Never normalize orthography — preserve exactly as printed. Volume II+ may follow; design everything corpus-level.

**Rights:** © Levon and Garegin Chugaszyan. Texts in copyright in Armenia until 2067-12-31 (life+70, d. 1997). A written heirs' licence must exist before public launch. New apparatus/metadata: CC BY 4.0.

## Architecture (decided — do not relitigate without cause)

1. **Extraction-first:** text layer via Docling or MinerU, diffed against `pdftotext`; vision-LLM passes are QA/labeling only, never primary text. Any LLM-vs-layer conflict resolves to the layer unless a human rules otherwise.
2. **TEI P5 (≥4.11) static-first:** one TEI file per article, jTEI-derived ODD; `teiCorpus` with standOff registers (persons, places, works, manuscripts). Published site is fully static (TEI Publisher 10 static export OR CETEIcean + Astro). No runtime database. Endings Principles compliant: every article readable with JS disabled.
3. **IIIF v3 for plates:** static level-0 tiles + Presentation 3 manifests; Mirador 4 for compare view, Clover for inline embeds; IIIF Content State URLs as the canonical deep-link/citation format for images.
4. **Retrieval ("Ask the corpus"):** the only dynamic component; isolatable and disposable. Hybrid: BGE-M3 (dense+sparse) + BM25 over lemmatized text + bge-reranker-v2-m3, on pgvector. Generation: Claude with Citations API; verification gate (LettuceDetect-style) before display; visible abstention. NEVER a Chookaszian persona.
5. **PIDs & preservation:** Zenodo concept DOI + per-article DOIs; JSON-LD `ScholarlyArticle` on every article page; versioned Zenodo release per milestone; Software Heritage for source; named 10-year steward in `GOVERNANCE.md`.

## Repository layout

```
/pipeline/        extraction, structuring, QA scripts (Python)
/tei/             one file per article: hy|ru|fr/<slug>.xml + corpus.xml + standoff/
/odd/             chookaszian.odd (jTEI-derived) + generated RNG/docs
/iiif/            tiles/ + manifests/ (plates: 24 pp. insert, Matenadaran miniatures)
/site/            static site source (Astro or TP10 export)
/rag/             chunker, indexer, eval/, api/
/eval/            CER benchmark set, retrieval QA set (see "Firsts")
/rights/          heirs licence, per-image clearance log, takedown policy
```

## Pipeline phases & acceptance criteria

**Phase 1 — Extraction & structure.** Split into articles validated against the printed ToC (pp. 572–573). Per article: title(s), original publication citation, body, footnotes (linked to anchors), bibliography. Acceptance: 100% ToC match; footnote count per article matches print; spot-check 10 articles by human.

**Phase 2 — TEI encoding.** Encode with `@xml:lang` per element/span: `hy` (reformed), `hy-arevela-classic` or project convention for classical orthography, `xcl` (Grabar), `xcl-Latn` (romanized), `ru`, `fr`, `en`. Footnotes as `<note place="bottom">`; original pagination as `<pb n="..."/>` (page-level citation anchor). Acceptance: valid against ODD; every page break present.

**Phase 3 — Enrichment (AI-assisted, human-reviewed).** NER via frontier LLM + gazetteers → `standOff` lists with `@ref` to Wikidata QIDs; manuscript shelfmarks via regex (pattern: Մատենադարան/Matenadaran ձեռ. NNNN and foreign sigla) → link to armenian-manuscripts-index.com and the Matenadaran global platform (launched 2026-07-22). References: GROBID first, LLM fallback for Armenian/Russian footnotes. Every AI-extracted entity carries `@resp` and review status; nothing unreviewed reaches the public site.

**Phase 4 — Site.** Two front doors: scholarly catalogue (per-article pages: TEI-rendered text, original citation, DOI, PDF facsimile page links, entities) + 2–3 curated story layers (biography/Matenadaran years; the Grigor Magistros–Shahnameh thread; the plates gallery). Typography: Noto Serif/Sans Armenian superfamily; measure 65–75ch; `lang` attribute per span. WCAG 2.2 AA is an acceptance criterion (focus not obscured by sticky viewer toolbars, targets ≥24px, drag alternatives in deep-zoom).

**Phase 5 — RAG.** Structure-aware chunking (never cross article boundaries; contextual prefix per chunk: article title + section; footnotes attached as metadata to anchor paragraphs). Answers must cite page + paragraph, linking to the article page anchor (and IIIF Content State for plates). Refuse when retrieval confidence is low: respond "the corpus does not address this." Acceptance: ≥90% citation accuracy on the in-house eval; zero uncited claims surfaced.

## AI ethics rules (binding)

- Label every AI-assisted output (entity extraction, translation drafts, summaries, QA) with tool, date, and human-review status. Site carries an AI methods statement page.
- Translations are two-tier and never blended: "AI draft, unrevised" (labelled, gisting only) vs "reviewed by [named scholar]". Heirs authorize any translation presented as Chookaszian's scholarship (Armenian moral rights).
- No free abstractive summaries — all summaries generated RAG-grounded from the article's own text and human-reviewed (LLM overgeneralization measured at 26–73%; RSOS Apr 2025).

## Publishable firsts (build as citable outputs, each with a Zenodo DOI)

1. Armenian scholarly-print OCR/CER benchmark (~100 lines across the corpus's orthographies/scripts) — none exists publicly.
2. Armenian retrieval/embedding eval (100–200 QA pairs from the corpus; SynDARin methodology) — required anyway before final model choice.
3. Grabar Bible-quotation detection (embedding similarity + CAVaL lemmatization vs Zohrab Bible).
4. RAG answer → cited sentence → IIIF facsimile region chain — no published system does this.

## Key tool versions (as of Jul 2026 — verify before install)

TEI P5 4.11.0 · TEI Publisher 10.x · Mirador 4.0.x · Docling / MinerU (latest) · BGE-M3 + bge-reranker-v2-m3 · pgvector · Calfa hye-calfa-n (github.com/calfa-co/hye-tesseract) for any print OCR · GROBID (latest) · Anthropic Citations API.

## What NOT to do

- Do not OCR pages that have a text layer. Do not let an LLM "improve" extracted text silently.
- Do not normalize classical → reformed orthography anywhere.
- Do not build an SPA-only site, a persona chatbot, or anything requiring a running server for reading.
- Do not publish AI-generated content without labels and review status.
- Do not mint identifiers outside the DOI/cool-URI scheme; article URLs are permanent once published.
