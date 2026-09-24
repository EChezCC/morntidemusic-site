# Jarvis — Cloudflare deploy for morntidemusic.com

Eric signed the look. Domain is still 503 because there is no Pages origin.

## Login
Cloudflare: eric.chez@gmail.com
Domain already in account: morntidemusic.com

## Preferred path: Direct Upload (images ship)
1. dash.cloudflare.com → Workers & Pages → Create → Pages → Upload assets
2. Project name: morntidemusic-site
3. Upload folder artifacts/Morntide_Site/ so these files exist at root:
   - index.html
   - assets/logo.jpg
   - assets/hero.jpg
   - assets/hero_radio.jpg
4. Deploy. Confirm https://morntidemusic-site.<account>.pages.dev returns the beach-desk page (not the GitHub stub).
5. Custom domains → Add:
   - morntidemusic.com
   - www.morntidemusic.com
6. Cloudflare will offer to create DNS automatically. Accept.
   If you must set records by hand in DNS → Records:
   - CNAME `www` → `morntidemusic-site.pages.dev` (Proxy on)
   - CNAME `@` (apex) → `morntidemusic-site.pages.dev` (flattened CNAME, Proxy on)
   Do not point A records at a random IP. Do not leave the zone with no apex record.
7. SSL/TLS = Full (strict) once the cert is issued. Wait until HTTPS is green.
8. Stop. Do not edit YouTube About until https://morntidemusic.com returns 200 with this page.

## Do not touch
Focus Radio encoder, Chezerecta, Path C, DistroKid, playlist deletes.
