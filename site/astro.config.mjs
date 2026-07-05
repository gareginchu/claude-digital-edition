import { defineConfig } from 'astro/config';

// The site is deployed to https://gareginchu.github.io/claude-digital-edition/.
// `site` is the canonical origin; `base` is the sub-path GH Pages uses when
// the repo is not the user root. Both must be set for internal links + og:url.
export default defineConfig({
  site: 'https://gareginchu.github.io',
  base: '/claude-digital-edition',
  outDir: '../site/dist',
  build: {
    // Emit index.html for every route so GH Pages resolves /articles/foo/ →
    // /articles/foo/index.html without a server.
    format: 'directory',
  },
});
