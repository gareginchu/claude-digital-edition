Astro site scaffold for the CLAUDE project.

Quickstart

1. Install Node.js (>=18) and npm.
2. From `site/` run:

```bash
npm install
npm run dev
```

The site expects pre-rendered TEI HTML files under `site/html/` (e.g., `site/html/example_article.html`). The `site/src/components/TeiList.astro` component lists those files at build time.
