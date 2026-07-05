# GitHub Pages Deployment

The repository is configured for automatic static site deployment to GitHub Pages.

## Setup (one-time)

1. Go to repository **Settings** → **Pages**
2. Under "Build and deployment":
   - **Source:** Select "GitHub Actions"
   - **Branch:** main (already configured)
3. Save

The `.github/workflows/deploy-pages.yml` workflow will now:
- Extract TEI from articles
- Render TEI → HTML
- Build RAG index
- Generate IIIF manifests
- Build Astro static site
- Deploy to `https://gareginchu.github.io/claude-digital-edition`

## Workflow Trigger

The deployment runs automatically on every push to `main`. Check the **Actions** tab for build logs.

## Site Preview

- Once deployed, visit: https://gareginchu.github.io/claude-digital-edition
- All 573 articles pre-rendered as static HTML
- Fast, no database, fully accessible without JavaScript

## Local Preview

To test locally before push:

```bash
cd site
npm install
npm run build
npm run preview
# Open http://localhost:3000
```

## Troubleshooting

- If workflow fails: Check **Actions** tab → failed job → logs for errors
- Common issues:
  - Node version mismatch (workflow uses node 18)
  - Missing PDF file (ensure `Babken_Chookaszian_Vol_I (2).pdf` is in root)
  - Python package install timeout (increase timeout in workflow)
