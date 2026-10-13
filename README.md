# morntidemusic.com

Public one-pager for Morntide Music.

Cloudflare Pages Direct Upload of artifacts/Morntide_Site/ is the deploy path.
See JARVIS_DNS.md.

## Build (GA4)

`python3 tools/build.py` writes `dist/` with GA4 gtag.js (G-29XZ8MKWQS) injected into every HTML page (Google verification file left untouched). Deploy `dist/`, not the repo root.
