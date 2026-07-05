// Prebuild helper. The article dynamic route (src/pages/articles/[slug].astro)
// reads fragments straight out of site/html/ at build time, so no copy is
// needed there. This script exists to stage the IIIF manifest under public/
// so Clover can fetch it at runtime, and to stage backmatter txt files for
// direct download.
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const siteDir = path.resolve(__dirname, '..');
const repoRoot = path.resolve(siteDir, '..');

const publicDir = path.join(siteDir, 'public');
fs.mkdirSync(publicDir, { recursive: true });

// 1. IIIF manifest → public/iiif/manifest.json for Clover's runtime fetch.
const manifestSrc = path.join(repoRoot, 'iiif', 'manifests', 'manifest.json');
const manifestDstDir = path.join(publicDir, 'iiif');
if (fs.existsSync(manifestSrc)) {
  fs.mkdirSync(manifestDstDir, { recursive: true });
  fs.copyFileSync(manifestSrc, path.join(manifestDstDir, 'manifest.json'));
  console.log('Staged IIIF manifest → public/iiif/manifest.json');
} else {
  console.log('No IIIF manifest found at', manifestSrc, '; skipping.');
}

// 2. Backmatter txt files → public/backmatter/ for direct-download links.
const bmSrc = path.join(repoRoot, 'pipeline', 'backmatter');
const bmDst = path.join(publicDir, 'backmatter');
if (fs.existsSync(bmSrc)) {
  fs.mkdirSync(bmDst, { recursive: true });
  for (const entry of fs.readdirSync(bmSrc)) {
    if (!entry.endsWith('.txt')) continue;
    fs.copyFileSync(path.join(bmSrc, entry), path.join(bmDst, entry));
  }
  console.log('Staged backmatter txt files → public/backmatter/');
}
