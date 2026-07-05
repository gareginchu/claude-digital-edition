import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

const siteDir = path.resolve(__dirname, '..');
const sourceDir = path.join(siteDir, 'html');
const publicArticlesDir = path.join(siteDir, 'public', 'articles');
const sourceBackmatterDir = path.resolve(siteDir, '..', 'pipeline', 'backmatter');
const publicBackmatterDir = path.join(siteDir, 'public', 'backmatter');

fs.mkdirSync(publicArticlesDir, { recursive: true });
fs.mkdirSync(publicBackmatterDir, { recursive: true });

if (!fs.existsSync(sourceDir)) {
  console.log('No site/html directory found; skipping article sync.');
  process.exit(0);
}

for (const entry of fs.readdirSync(sourceDir)) {
  if (!entry.endsWith('.html')) continue;
  fs.copyFileSync(path.join(sourceDir, entry), path.join(publicArticlesDir, entry));
}

if (fs.existsSync(sourceBackmatterDir)) {
  for (const entry of fs.readdirSync(sourceBackmatterDir)) {
    if (!entry.endsWith('.txt')) continue;
    fs.copyFileSync(path.join(sourceBackmatterDir, entry), path.join(publicBackmatterDir, entry));
  }
}

console.log('Synced pre-rendered article HTML and backmatter text into site/public');
