# morntidemusic.com

Static site for Morntide Music: home one-pager + one page per YouTube release (djchezerecta.com pattern).

## Data
- `tools/update.py` → `data/catalog.json` (every public, non-live, non-Short long-form upload: description, chapters, mood, verified store links),
  `data/shorts.json` (Shorts + parent video from their description link), `data/playlists.json`.
  Fail-closed: a video is excluded unless yt-dlp confirms `availability=public` and not live/upcoming; zero videos aborts.
  `YTDLP_META_DIR=dir` reuses fresh (<24 h) `yt-dlp -J` files (`<id>.json`, `s_<id>.json` for Shorts).
- Slugs come from the title and are pinned in catalog.json once written (URLs never change on a retitle).
- Mood: FOCUS/RISE/SLEEP playlist first, then Deep Work Blocks → FOCUS, RELAX/First Light Sessions → RISE, anything else → SLEEP.
- Store links: only kept when the store page names Morntide (Spotify checked via its embed page). Unverifiable links are dropped.

## Build / check / deploy
- `python3 tools/build.py` → `dist/`: home (+Latest releases), `/releases/`, `/releases/<slug>/`, `/focus/ /rise/ /sleep/`, `404.html`, `_redirects` (`/spa-bowls/` → Spa Room page), `sitemap.xml`. GA4 G-29XZ8MKWQS injected (`GA4_ID=` disables). JSON-LD: VideoObject (+Clip chapters), MusicRecording, BreadcrumbList, ItemList.
- `tools/check_links.sh` — internal links resolve, external links 2xx/3xx.
- Preview: `wrangler pages deploy dist --project-name morntidemusic-site --branch feature-releases`. Production deploys only from `main`.

## CI: `ci/auto-update.yml` (inactive; move to `.github/workflows/` to activate)
Daily update → build → link check → deploy → commit data. Secrets: `CLOUDFLARE_API_TOKEN` (Pages:Edit, this account), `CLOUDFLARE_ACCOUNT_ID`.
yt-dlp is often bot-blocked on GitHub runners; the run then fails closed and nothing deploys.

See JARVIS_DNS.md for DNS.
