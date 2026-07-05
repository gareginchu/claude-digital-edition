# ⚡ GitHub Pages: 30-Second Setup

Your static site + 573 pre-rendered TEI HTML pages are **ready to deploy**.

## Enable Pages (Click 3 buttons)

1. Go to: https://github.com/gareginchu/claude-digital-edition/settings/pages
2. Under **Source**, select: **GitHub Actions** (dropdown)
3. Save

**Done.** The `deploy-pages.yml` workflow will auto-run on every push to `main`.

Site goes live at: **https://gareginchu.github.io/claude-digital-edition**

---

## What the Workflow Does (Auto)

Every push triggers:
```
PDF extract → TEI gen → TEI→HTML (573 pages) → RAG index → IIIF manifest → Astro build → Deploy to Pages
```

Total build time: ~15-20 minutes (first time longer).

---

## Current Build Status

Check: https://github.com/gareginchu/claude-digital-edition/actions

- Green ✅ = Workflow succeeded
- Red ❌ = Check logs for error

---

## Site Structure (Once Live)

```
https://gareginchu.github.io/claude-digital-edition/
├── index.html              ← Homepage with article list
├── article_001.html        ← Pre-rendered TEI HTML
├── article_002.html
├── ...article_573.html
└── (Astro static assets)
```

All pages are **fully static** — no server, no JavaScript required.

---

## Troubleshooting

### Workflow still pending?
- Wait 15–20 minutes (first run is slower)
- Check **Actions** tab for live progress

### 404 on site?
- Deployment may still be running
- Check repo settings: Pages source should be **GitHub Actions**

### Want to disable auto-deploy?
- Rename `.github/workflows/deploy-pages.yml` to `deploy-pages.yml.bak`
- Push the change

### Want to rebuild manually?
- Go to **Actions** tab
- Click "Deploy site to GitHub Pages"
- Click "Run workflow"

---

## What You Get

- ✅ All 573 articles published
- ✅ Full-text searchable (via browser Ctrl+F)
- ✅ Original pagination preserved (`<pb>` elements)
- ✅ Armenian script properly encoded (UTF-8)
- ✅ Zero downtime
- ✅ Free hosting (GitHub Pages)
- ✅ HTTPS by default

---

## Next: Rich Features

Once Pages is live, you can add:

- **Search bar** (Algolia, Typesense, or Meilisearch)
- **IIIF viewer** (Mirador 4) for plates gallery
- **RAG retrieval** ("Ask the corpus")
- **Entity linking** (click names → Wikidata)
- **Multi-language UI** (Armenian/Russian/French/English)

See `PAGES_SETUP.md` for detailed local preview instructions.
