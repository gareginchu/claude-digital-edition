# IIIF plates pipeline

Static IIIF v3 delivery of the 23-page plates insert (pp. 549-571 of
`Babken_Chookaszian_Vol_I (2).pdf`, second expanded edition Yerevan
2022/2023). Includes 14 photographic portraits (folios I-XIV) and 9
Matenadaran miniatures (folios XIV-XXIII).

The output is a **Presentation API 3.0** Manifest plus one **Image API 3.0**
level-0 static tile hierarchy per plate. Everything is precomputed; a
plain static file server (nginx, S3, GitHub Pages, etc.) can host it.
Nothing here needs to run at request time.

> CLAUDE.md mandates IIIF v3 (Presentation 3, Image 3) and level-0 static
> tiles for plates. This pipeline satisfies both.

## Rights status (READ FIRST)

The plates are **not cleared for public distribution.** Miniatures are
reproduced from Matenadaran manuscripts and require per-shelfmark
clearance from the Matenadaran plus the heirs' licence (© Levon and
Garegin Chugaszyan; life+70 until 2067-12-31). The generated
`manifest.json` is stamped with:

- `rights: http://rightsstatements.org/vocab/InC-RUW/1.0/`
- a `Public visibility` metadata field valued `pending rights clearance`

Do **not** push tiles or the manifest to a public CDN, GitHub Pages, or
any remote host until the licence chain is signed. Local review only.
The pipeline outputs (`iiif/tiles/`, `iiif/pages/`) are gitignored and
must never be committed.

## Pipeline

```
Babken_Chookaszian_Vol_I (2).pdf
        |
        v
iiif/extract_plates.py    (PyMuPDF -> Pillow: renders each plate page as JPEG)
        |
        v
iiif/pages/plate_NN.jpg  +  iiif/pages/captions.json
        |
        v
iiif/build_tiles.py       (Pillow: level-0 static Image API 3 tree per plate)
        |
        v
iiif/tiles/plate_NN/
    info.json
    full/max/0/default.jpg
    full/1024,X/0/default.jpg   (+ 512, 256)
    <x>,<y>,<w>,<h>/<w>,<h>/0/default.jpg  (tile grid, 512x512)
        |
        v
iiif/create_manifest.py   (Presentation 3 Manifest: one Canvas per plate)
        |
        v
iiif/manifests/manifest.json
```

Run everything in one go:

```powershell
python iiif/extract_plates.py
python iiif/build_tiles.py
python iiif/create_manifest.py
```

### Options

| Script | Useful flags |
|---|---|
| `extract_plates.py` | `--dpi 200` (default), `--start 549 --end 571`, `--out iiif/pages` |
| `build_tiles.py` | `--base https://cdn.example.org/iiif` (image-service base URL to embed in `info.json`) |
| `create_manifest.py` | `--base ...` (image-service base), `--manifest-id https://.../manifests/chookaszian-plates` |

## Windows install

`pymupdf` ships pre-built wheels for Windows on Python 3.9 - 3.13, so no
Poppler or MuPDF native install is needed (this is why the pipeline uses
PyMuPDF, not `pdf2image`).

```powershell
# From the repo root, ideally in a virtualenv.
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

Only two direct dependencies matter for this pipeline: `pymupdf>=1.24`
and `Pillow>=10.0`. If you want the minimal install:

```powershell
python -m pip install "pymupdf>=1.24" "Pillow>=10.0"
```

If a Windows console mangles the Armenian captions when scripts print to
stdout, run inside a UTF-8 console:

```powershell
$env:PYTHONIOENCODING = "utf-8"
python iiif/extract_plates.py
```

## Output layout (level 0 static compliance)

For every plate the tile builder produces the file grammar mandated by
[Image API 3.0 section 4](https://iiif.io/api/image/3.0/#4-image-requests):

```
iiif/tiles/plate_01/
  info.json                                      -> ImageService3, profile=level0
  full/max/0/default.jpg                         -> whole image, native size
  full/1024,1325/0/default.jpg                   -> whole image, 1024 wide
  full/512,662/0/default.jpg
  full/256,331/0/default.jpg
  0,0,512,512/512,512/0/default.jpg              -> tile grid, scaleFactor=1
  512,0,512,512/512,512/0/default.jpg
  ...
```

`info.json` advertises the whole-image `sizes` list and a single 512x512
`tiles` block at scale factor 1; that is the level-0 compliance target
and is what Clover / OpenSeadragon consume.

## Deployment: swapping the base URL

Both `info.json` files and the Presentation manifest embed a base URL for
the Image API service. The default placeholder is
`https://REPLACE-ME.example.org/iiif`. Re-run the pipeline with the real
base once you know it:

```powershell
$env:PUBLIC_BASE = "https://iiif.chookaszian.example.org/iiif"
$env:MANIFEST_BASE = "https://chookaszian.example.org/manifests"
python iiif/build_tiles.py --base $env:PUBLIC_BASE
python iiif/create_manifest.py --base $env:PUBLIC_BASE --manifest-id "$env:MANIFEST_BASE/chookaszian-plates"
```

To host on the same origin as the Astro site, upload `iiif/tiles/*` to a
directory reachable at `<base>/plate_NN/...` and `iiif/manifests/manifest.json`
to any URL and pass that URL to the viewer.

For **local review only**, copy the manifest to `site/public/iiif/manifest.json`
and the whole `iiif/tiles/` tree to `site/public/iiif/`. The plates page
loads the manifest from `/iiif/manifest.json` by default. (No CDN push.
No public URL.)

## Site integration

`site/src/pages/plates.astro` embeds the manifest via the
[Clover IIIF viewer](https://samvera-labs.github.io/clover-iiif/) as a
web component, loaded from the esm.sh CDN so no `npm install` is
required for local review. Before production, vendor the JS or add
`@samvera/clover-iiif` as an npm dependency in `site/package.json`.

The page also renders a JS-free fallback list -- thumbnails + captions +
direct links to the level-0 `full/max` JPEG for each plate -- so the
content is readable without the viewer. This satisfies the CLAUDE.md
requirement that every page be readable with JavaScript disabled
(Endings Principles) and helps with WCAG 2.2 AA.

## Content-State citation URLs (permanent deep links)

The canonical citation format for a plate region is a
[IIIF Content State v1](https://iiif.io/api/content-state/1.0/) URL: a
Base64URL-encoded, JSON-serialized W3C Web Annotation whose target is a
specific Canvas (optionally with a fragment selector for a sub-region).

Example -- linking Canvas #1 (Plate 1, portraits page):

1. Author the JSON:

   ```json
   {
     "@context": "http://iiif.io/api/presentation/3/context.json",
     "id": "https://chookaszian.example.org/citations/plate_01",
     "type": "Annotation",
     "motivation": "contentState",
     "target": {
       "id": "https://iiif.chookaszian.example.org/iiif/canvas/plate_01",
       "type": "Canvas",
       "partOf": [{
         "id": "https://chookaszian.example.org/manifests/chookaszian-plates",
         "type": "Manifest"
       }]
     }
   }
   ```

2. UTF-8 encode, then Base64URL encode without padding. In Python:

   ```python
   import base64, json
   state = {...}  # dict above
   encoded = base64.urlsafe_b64encode(json.dumps(state).encode("utf-8")).rstrip(b"=").decode()
   ```

3. Deliver as the fragment of a viewer URL, e.g.

   ```
   https://chookaszian.example.org/plates/#iiif-content=<encoded>
   ```

   Clover reads `?iiif-content=` (query) or `#iiif-content=` (fragment)
   and jumps to the target Canvas.

To pin a region within a plate, add a fragment `#xywh=` selector to the
target id (Presentation 3.0 canvas selector syntax) before encoding:

```json
"target": {
  "id": "https://iiif.chookaszian.example.org/iiif/canvas/plate_18#xywh=200,400,800,600",
  "type": "Canvas",
  "partOf": [ ... ]
}
```

RAG-generated answers that cite a plate must emit Content-State URLs of
this form (CLAUDE.md "Publishable firsts" #4: RAG answer -> cited
sentence -> IIIF facsimile region chain).

## Known gaps

- The tile builder only emits scale factor 1 (native resolution). For
  larger source images we would add downsampled scale-factor 2 and 4
  tile grids; the 1700x2200 renders here don't warrant them.
- Captions are scraped from the PDF text layer; miniature shelfmarks
  (e.g. Matenadaran ձեռ․ 10525) are visible in `iiif/pages/captions.json`
  but are not yet linked into the standoff manuscript register. That
  belongs in Phase 3 enrichment, not the IIIF pipeline.
- `create_manifest.py` does not currently generate a `structures` range
  (photos vs miniatures). Easy to add once the two sections are formally
  cataloged.
