# Deep-Research Prompt: AI for Philological Heritage — State of the Art & Best Cases

> Paste this prompt into Claude (Research mode) or assign it to a dedicated research
> subagent. Replace bracketed placeholders before running.

---

## Role

You are a senior digital-humanities strategist and web designer specialising in
AI-assisted cultural-heritage production. You combine three literacies: (1) academic
philology and medieval studies, (2) modern AI/LLM tooling, and (3) public-facing
digital presentation (web, interactive, archival).

## Object of Study

I hold the collected articles of **[SCHOLAR NAME]** — a renowned historian, linguist,
and expert in medieval literary works — as a **scanned/typeset PDF book** in
**[LANGUAGE(S), e.g. Armenian, Russian, English, with quoted passages in Classical
Armenian (Grabar), Greek, Latin]**. The corpus includes: textual criticism, manuscript
studies, etymology, historical commentary, illustrations/plates of manuscripts, and a
dense scholarly apparatus (footnotes, bibliography, indices).

## Mission

Produce a structured intelligence report (3,000–5,000 words + source list) covering
the **latest developments (prioritise the last 24 months)** in AI applied to
philological and medieval-heritage material, and the **best real-world cases** of
analysing and presenting such heritage. The report will directly feed a technical
specification (CLAUDE.md) for building a digital edition and public web presentation
of this book.

## Research Axes

### 1. Text acquisition from scholarly PDFs
- Current best OCR/HTR for multi-script, footnote-heavy academic books: Transkribus,
  eScriptorium/Kraken, Google Document AI, Azure Document Intelligence, Surya,
  and vision-LLM OCR (Claude, GPT-4V/o-series, Gemini) — accuracy on
  **[non-Latin script, e.g. Armenian]**, diacritics, mixed-language lines.
- Layout analysis: separating body text, footnotes, apparatus criticus, captions,
  running heads; recovering logical structure (article boundaries, headings).
- Post-correction workflows: LLM-assisted OCR correction, human-in-the-loop QA,
  measurable CER/WER benchmarks reported for comparable projects.

### 2. AI analysis of philological content
- Named-entity recognition for historical persons, places, manuscripts (shelfmarks),
  works, and dates in medieval-studies text; multilingual/ancient-language NER models.
- Citation and cross-reference extraction (biblical, classical, manuscript sigla).
- Semantic linking to authority files: VIAF, Wikidata, Pleiades, Pinakes,
  **[domain authorities, e.g. Matenadaran catalogues, Armenian Manuscript databases]**.
- LLM-based summarisation and abstracting of dense scholarly articles without
  distortion; approaches to hallucination control in scholarly contexts (RAG over the
  corpus itself, citation-grounded generation, refusal thresholds).
- Etymology/lexicography-specific AI work (relevant if the corpus includes linguistic
  articles): computational etymology, historical-lexicon digitisation projects.
- Stylometry and authorship/attribution tooling where relevant to medieval texts.

### 3. Standards and data models
- TEI-XML current practice for born-digital editions of collected scholarly papers
  (not just primary sources) — TEI Publisher, TEI Processing Model, CETEIcean.
- IIIF (Image API + Presentation API v3) for plates and manuscript images; Mirador 4
  and Universal Viewer state of play.
- Linked Open Data patterns for humanities (CIDOC-CRM, LIDO where museum objects
  appear); persistent identifiers (DOI, Handle, ARK) for article-level citation.

### 4. Retrieval and conversational access
- RAG architectures proven on humanities corpora: chunking strategies for footnoted
  scholarly prose, multilingual embeddings quality for **[LANGUAGE(S)]**
  (e.g. multilingual-e5, BGE-M3, Voyage, Cohere), hybrid BM25+dense retrieval.
- "Chat with the archive" deployments by libraries/museums — which ones are respected
  by the scholarly community, which drew criticism, and why.
- Question-answering with verifiable citation back to page/paragraph of the source PDF.

### 5. Presentation & web design best cases
Identify 8–12 exemplary projects and dissect each (institution, stack, AI components,
design language, what to imitate, what to avoid). Prioritise:
- Digital scholarly editions and collected-works portals (e.g. recent TEI Publisher
  showcases, e-editiones community projects).
- Manuscript-heritage platforms: e.g. Vatican DigiVatLib, Fragmentarium, e-ktobe,
  Transkribus-derived portals, Cambridge Digital Library, **[regional exemplars,
  e.g. Matenadaran digital initiatives, Calouste Gulbenkian–funded Armenian projects]**.
- AI-enhanced storytelling in GLAM: Smithsonian, Europeana generative-AI pilots,
  Google Arts & Culture experiments — with critical assessment.
- Interactive visualisations: timelines (vis-timeline and successors), geographic
  layers, network graphs of persons/manuscripts, side-by-side facsimile + transcript.
- Typography and multilingual web design for the scripts involved; accessible design
  (WCAG 2.2) for long-form scholarly reading.

### 6. Ethics, rights, and scholarly acceptance
- Copyright status handling for a 20th–21st-century scholar's articles (estate
  permissions, publisher rights on offprints).
- Community norms on AI-generated summaries/translations of scholarship: disclosure,
  labelling, review requirements emerging in DH journals and library policy.
- Preservation: OAIS-aligned archiving, static-site longevity vs. dynamic apps.

## Method Requirements

- Search in English **and** in **[other relevant languages]**; scholarly sources
  (DH journals, conference proceedings — DH, EADH, CHR, ICDAR, IIIF community) take
  precedence over vendor marketing.
- Date-stamp every claim; flag anything older than 2023 as "established practice"
  vs. newer items as "emerging".
- For each best case, capture at least one screenshot-worthy URL for a design-reference
  moodboard.
- Where evidence conflicts (e.g. OCR benchmark claims), present both sides and state
  your confidence.

## Deliverable Format

1. **Executive summary** (max 400 words) — the five decisions this research settles.
2. **Findings by axis** (sections 1–6 above), each ending with "Implications for our
   build" (3–5 bullets max).
3. **Best-case gallery** — table: project | institution | AI used | stack | steal-worthy
   ideas | pitfalls.
4. **Recommended reference architecture** — one paragraph + component list naming
   concrete tools/models, ready to be transcribed into a CLAUDE.md specification.
5. **Source list** with dates and one-line relevance notes.
