# Jarvis — morntidemusic.com deploy

Eric approved the look 2026-09-24. Domain spelling locked: **morntidemusic.com**.

## Login
- Cloudflare account: eric.chez@gmail.com
- Domain already in that account (registered 2026-08-22)

## What to publish
Static folder artifacts/Morntide_Site/ (index.html + assets/logo.jpg + assets/hero.jpg + assets/hero_radio.jpg).
GitHub repo EChezCC/morntidemusic-site is the Pages connection target — if images are missing on GitHub, use Direct Upload of the artifacts folder instead.

## Cloudflare Pages
1. Create project `morntidemusic-site` from Git or Direct Upload.
2. No build. Output `/`.
3. Custom domains: morntidemusic.com and www.morntidemusic.com
4. Apex + www CNAME/ALIAS to the Pages target.
5. Wait for HTTPS green.

## After it serves
Ask-first before YouTube About. Then website = https://morntidemusic.com on new descriptions only.

## Do not touch
Focus Radio encoder, Chezerecta Radio, Path C, DistroKid, playlist deletes.
