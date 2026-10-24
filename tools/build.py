#!/usr/bin/env python3
"""Build dist/ for Cloudflare Pages Direct Upload.
Static files are copied as-is; generated from data/catalog.json (tools/update.py):
  /releases/ index, /releases/<slug>/ per video (facade embed, description, chapters, verified store links,
  Shorts, VideoObject + MusicRecording + BreadcrumbList JSON-LD), mood hubs /focus/ /rise/ /sleep/,
  "Latest releases" on the home page, 404.html, _redirects, sitemap.xml (with video:video).
GA4 gtag.js (G-29XZ8MKWQS, anonymize_ip, no signals/ad personalization, loaded 1.5 s after load) goes into
every HTML page; Google verification files are copied untouched. GA4_ID= (empty) disables it.
Fail-closed: the build aborts if any release lacks a page, a sitemap entry, or valid JSON-LD."""
import html, json, os, pathlib, re, shutil
GA = os.environ.get("GA4_ID", "G-29XZ8MKWQS").strip()
R = pathlib.Path(__file__).resolve().parent.parent
D = R / "dist"; SITE = "https://morntidemusic.com"
CAT = json.loads((R / "data/catalog.json").read_text())
SHORTS = json.loads((R / "data/shorts.json").read_text())
PL = {p["id"]: p for p in json.loads((R / "data/playlists.json").read_text())}
SLUGS = json.loads((R / "data/slugs.json").read_text())
for c in CAT:   # data/slugs.json is the single source of truth for URLs
    assert c["id"] in SLUGS, f"no pinned slug for {c['id']} (run tools/update.py)"
    c["slug"] = SLUGS[c["id"]]
assert len({c["slug"] for c in CAT}) == len(CAT), "duplicate slugs"
assert all(re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+){1,5}", c["slug"]) for c in CAT), "bad slug format"
BYID = {c["id"]: c for c in CAT}
MOODS = {
 "focus": ("FOCUS", "Focus music for deep work", "Morning piano, soft electronic and ambient beds for deep work, coding and study. No lyrics, no drops. Pick one task and stay with it.", ["PLUp6gLFHAa3E", "PLe1cGzmYaAX0"]),
 "rise": ("RISE", "Calm music to start the day", "Warm morning sessions with a little more lift, from First Light to singing bowls. Calm enough to work to, bright enough to wake up with.", ["PLSmZ4mxAy_Sg", "PLKj69vZNgz7s", "PLH3nuFmJ72Ds"]),
 "sleep": ("SLEEP", "Sleep and night ambient", "Ocean waves, night rain and soft night ambient for winding down and long sleep. No vocals, no sudden changes.", ["PLF2-pms8eUrY"]),
}
e = lambda s: html.escape(str(s), quote=True)
SNIP = ('' if not GA else '<script>window.dataLayer=window.dataLayer||[];function gtag(){dataLayer.push(arguments)}gtag("js",new Date());'
        f'gtag("config","{GA}",{{anonymize_ip:true,allow_google_signals:false,allow_ad_personalization_signals:false}});'
        'addEventListener("load",function(){setTimeout(function(){var s=document.createElement("script");s.async=1;'
        f's.src="https://www.googletagmanager.com/gtag/js?id={GA}";document.head.appendChild(s)}},1500)}});</script>')
SKIP = {"dist", "tools", "node_modules", "data", "ci"}
NOCOPY = {"README.md", "JARVIS_DNS.md", "sitemap.xml"}
NONSITE_EXT = {".md", ".py", ".toml", ".lock", ".log", ".yml"}

def clean_title(t): return re.sub(r"\s*[|·]\s*Morntide\s*$", "", t, flags=re.I).strip()
def iso(s): h, m, x = s // 3600, s % 3600 // 60, s % 60; return "PT" + (f"{h}H" if h else "") + (f"{m}M" if m else "") + f"{x}S"
def hms(s): h, m, x = s // 3600, s % 3600 // 60, s % 60; return f"{h}:{m:02d}:{x:02d}" if h else f"{m}:{x:02d}"
def human(s):
    h, m = s // 3600, round(s % 3600 / 60)
    if m == 60: h, m = h + 1, 0
    return (f"{h} hr" + ("s" if h > 1 else "") if h else "") + (f" {m} min" if m and h < 8 else "") if h else f"{m} min"
def rurl(c): return f"/releases/{c['slug']}/"
def summary(c):
    """First paragraph of the YouTube description (no links, hashtags, chapters)."""
    ps = paras(c)
    return (ps[0] if ps else clean_title(c["title"]))[:300]
def paras(c):
    out, cur = [], []
    for ln in (c["description"] or "").splitlines():
        s = ln.strip()
        if re.match(r"^chapters?:?$", s, re.I) or re.match(r"^\(?\d{1,2}:\d{2}", s): break
        if not s:
            if cur: out.append(cur); cur = []
            continue
        if "http" in s or s.startswith("#") or s.lower().startswith(("subscribe", "more from")): continue
        cur.append(s)
    if cur: out.append(cur)
    res = []
    for p in out:
        p = [x for x in p if not (x.endswith(":") and len(p) == 1)]
        if not p: continue
        if all(x.startswith("- ") for x in p[1:]) and len(p) > 1 and p[0].endswith(":"):
            res.append(("list", p[0], [x[2:] for x in p[1:]]))
        else: res.append(" ".join(p))
    return [r for r in res if isinstance(r, str)] if False else res
def first_text(c):
    for p in paras(c):
        if isinstance(p, str): return p[:300]
    return clean_title(c["title"])

src_index = (R / "index.html").read_text()
STYLE = re.search(r"<style>(.*?)</style>", src_index, re.S).group(1)
FONTS = '\n'.join(l for l in src_index.splitlines() if "fonts.g" in l)
EXTRA = """
    .page { padding: 48px 0 80px; }
    .crumbs { font-size: 13px; letter-spacing: .06em; color: var(--gold-soft); margin-bottom: 18px; }
    .crumbs a { text-decoration: underline; text-underline-offset: 3px; }
    .page h1 { max-width: none; font-family: "Cormorant Garamond", serif; font-weight: 500; font-size: clamp(32px, 5vw, 54px); line-height: 1.08; margin-bottom: 14px; }
    .meta { color: var(--gold-soft); font-size: 14px; letter-spacing: .06em; margin-bottom: 24px; }
    .chip { display: inline-block; border: 1px solid rgba(232,196,120,.5); border-radius: 999px; padding: 3px 10px; font-size: 12px; letter-spacing: .12em; color: var(--gold); text-transform: uppercase; }
    .prose { max-width: 720px; margin-top: 28px; line-height: 1.65; color: var(--mist); font-weight: 300; }
    .prose p, .prose ul { margin-bottom: 14px; } .prose ul { padding-left: 20px; }
    .page h2 { font-family: "Cormorant Garamond", serif; font-weight: 500; font-size: 30px; margin: 40px 0 14px; color: var(--cream); }
    .chapters { list-style: none; max-width: 720px; columns: 2 280px; column-gap: 28px; }
    .chapters li { break-inside: avoid; padding: 7px 0; border-bottom: 1px solid rgba(232,196,120,.12); }
    .chapters a { display: flex; gap: 14px; } .chapters time { color: var(--gold); font-variant-numeric: tabular-nums; min-width: 64px; }
    .grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(250px, 1fr)); gap: 22px; margin-top: 26px; }
    .card { display: block; background: rgba(20,38,51,.7); border: 1px solid rgba(232,196,120,.16); border-radius: 14px; overflow: hidden; }
    .card img { aspect-ratio: 16/9; object-fit: cover; width: 100%; }
    .card .ct { padding: 14px 16px 16px; } .card h3 { font-size: 16px; font-weight: 500; line-height: 1.35; margin: 8px 0 6px; }
    .card .d { color: var(--gold-soft); font-size: 13px; }
    .moods { display: flex; flex-wrap: wrap; gap: 10px; margin-top: 18px; }
    .lane a { display: block; }
    .latest { padding: 72px 0 24px; }
    .latest h2 { font-family: "Cormorant Garamond", serif; font-weight: 500; font-size: clamp(30px, 4vw, 44px); }
    .page .frame { margin-top: 8px; }
    @media (max-width: 760px) { nav ul { display: none; } .chapters { columns: 1; } }
"""
NAV = """  <nav>
    <div class="wrap">
      <a class="brand" href="/"><img src="/assets/logo.jpg" alt="Morntide" width="42" height="42" />Morntide</a>
      <ul>
        <li><a href="/player/">Music Player</a></li>
        <li><a href="/releases/">Releases</a></li>
        <li><a href="/focus/">Focus</a></li>
        <li><a href="/rise/">Rise</a></li>
        <li><a href="/sleep/">Sleep</a></li>
        <li><a href="/#radio">Radio</a></li>
      </ul>
      <a class="btn" href="https://www.youtube.com/@Morntidemusic?sub_confirmation=1">Subscribe</a>
    </div>
  </nav>"""
FOOT = re.search(r"  <footer>.*?</footer>", src_index, re.S).group(0)
FACADE_JS = re.search(r"  <script>\s*document\.querySelectorAll\('\.yt-lite'\).*?</script>", src_index, re.S).group(0)

def shell(path, title, desc, body, ld, img=None, robots="index, follow"):
    url = SITE + path
    img = img or SITE + "/assets/hero.jpg"
    lds = "".join(f'\n  <script type="application/ld+json">{json.dumps(x, ensure_ascii=False)}</script>' for x in ld)
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>{e(title)}</title>
  <meta name="description" content="{e(desc)}" />
  <link rel="canonical" href="{e(url)}" />
  <meta name="robots" content="{robots}" />
  <meta property="og:type" content="website" />
  <meta property="og:site_name" content="Morntide" />
  <meta property="og:url" content="{e(url)}" />
  <meta property="og:title" content="{e(title)}" />
  <meta property="og:description" content="{e(desc)}" />
  <meta property="og:image" content="{e(img)}" />
  <meta name="twitter:card" content="summary_large_image" />
  <link rel="icon" href="/assets/logo.jpg" />
{FONTS}
  <style>{STYLE}{EXTRA}</style>{lds}
</head>
<body>
{NAV}
  <main class="page"><div class="wrap">
{body}
  </div></main>
{FOOT}
{FACADE_JS}
</body>
</html>
"""
def embed(c, autoplay=False):
    """Visible YouTube player (iframe) -- same as djchezerecta release pages' video player, loaded with the page."""
    t = clean_title(c["title"])
    return (f'<div class="frame player-frame"><iframe src="https://www.youtube-nocookie.com/embed/{c["id"]}?rel=0&amp;playsinline=1{"&amp;autoplay=1" if autoplay else ""}" '
            f'title="{e(t)} | Morntide" allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture; web-share" '
            f'referrerpolicy="strict-origin-when-cross-origin" allowfullscreen></iframe></div>'
            f'<noscript><p class="sub"><a href="https://www.youtube.com/watch?v={c["id"]}">Watch on YouTube →</a></p></noscript>')
def card(c):
    return (f'<a class="card" href="{rurl(c)}"><img src="{e(c["thumb"])}" alt="{e(clean_title(c["title"]))}" width="480" height="270" loading="lazy" decoding="async" />'
            f'<div class="ct"><span class="chip">{MOODS[c["mood"]][0]}</span><h3>{e(clean_title(c["title"]))}</h3><p class="d">{human(c["duration"])}</p></div></a>')
def facade(c):
    t = clean_title(c["title"])
    return (f'<div class="frame"><a class="yt-lite" href="https://www.youtube.com/watch?v={c["id"]}" data-id="{c["id"]}" data-title="{e(c["title"])}" aria-label="Play {e(t)}">'
            f'<img src="{e(c["thumb"])}" alt="{e(t)} by Morntide" width="1280" height="720" decoding="async" fetchpriority="high" />'
            f'<span class="play" aria-hidden="true"><svg viewBox="0 0 24 24"><path d="M8 5v14l11-7z"/></svg></span><span class="len" aria-hidden="true">{human(c["duration"])}</span></a></div>'
            f'<noscript><p class="sub"><a href="https://www.youtube.com/watch?v={c["id"]}">Watch on YouTube →</a></p></noscript>')
ORG = {"@type": "MusicGroup", "name": "Morntide", "url": SITE + "/", "sameAs": ["https://www.youtube.com/@Morntidemusic"]}
def crumbs_ld(items): return {"@context": "https://schema.org", "@type": "BreadcrumbList", "itemListElement": [{"@type": "ListItem", "position": i + 1, "name": n, "item": SITE + u} for i, (n, u) in enumerate(items)]}
def release(c):
    t = clean_title(c["title"]); mood = MOODS[c["mood"]]; url = SITE + rurl(c)
    desc = first_text(c)
    body = [f'<p class="crumbs"><a href="/">Home</a> › <a href="/releases/">Releases</a> › <a href="/{c["mood"]}/">{mood[0].title()}</a></p>',
            f'<h1>{e(t)}</h1>', f'<p class="meta"><span class="chip">{mood[0]}</span> · {human(c["duration"])} · {e(c["upload_date"][:10])}</p>', embed(c)]
    acts = [f'<a class="btn" href="/player/?v={c["id"]}">▶ Open in Music Player</a>', f'<a class="btn ghost" href="https://www.youtube.com/watch?v={c["id"]}">Watch on YouTube</a>']
    acts += [f'<a class="btn ghost" href="https://www.youtube.com/playlist?list={p}">Open {e(PL[p]["label"])} playlist</a>' for p in c["playlists"]]
    acts.append(f'<a class="btn ghost" href="/{c["mood"]}/">More {mood[0].title()} releases</a>')
    body.append('<div class="actions">' + "".join(acts) + '</div>')
    if c["stores"]:
        body.append('<h2>Stream it</h2><div class="actions">' + "".join(f'<a class="btn ghost" href="{e(s["url"])}" rel="noopener">{e(s["name"])}</a>' for s in c["stores"]) + '</div>')
    pr = []
    for p in paras(c):
        if isinstance(p, str): pr.append(f"<p>{e(p)}</p>")
        else: pr.append(f"<p>{e(p[1])}</p><ul>" + "".join(f"<li>{e(x)}</li>" for x in p[2]) + "</ul>")
    if pr: body.append('<h2>About this session</h2><div class="prose">' + "".join(pr) + '</div>')
    if c["chapters"]:
        body.append(f'<h2>Chapters</h2><ol class="chapters">' + "".join(
            f'<li><a href="https://www.youtube.com/watch?v={c["id"]}&amp;t={ch["t"]}s"><time datetime="{iso(ch["t"])}">{hms(ch["t"])}</time><span>{e(ch["title"])}</span></a></li>' for ch in c["chapters"]) + '</ol>')
    sh = [s for s in SHORTS if s["parent"] == c["id"]]
    if sh: body.append('<h2>Shorts</h2><div class="actions">' + "".join(f'<a class="btn ghost" href="https://www.youtube.com/shorts/{s["id"]}">{e(re.sub(r"\s*#\S+", "", s["title"]).strip() or "Watch the Short")}</a>' for s in sh) + '</div>')
    more = [x for x in CAT if x["mood"] == c["mood"] and x["id"] != c["id"]][:3]
    if more: body.append(f'<h2>More {mood[0].title()}</h2><div class="grid">' + "".join(card(x) for x in more) + '</div>')
    vo = {"@context": "https://schema.org", "@type": "VideoObject", "@id": url + "#video", "name": c["title"], "description": desc,
          "thumbnailUrl": [c["thumb"]], "uploadDate": c["upload_date"], "duration": iso(c["duration"]),
          "embedUrl": f"https://www.youtube-nocookie.com/embed/{c['id']}", "contentUrl": f"https://www.youtube.com/watch?v={c['id']}",
          "url": url, "publisher": ORG, "isFamilyFriendly": True}
    if c["chapters"]:
        vo["hasPart"] = [{"@type": "Clip", "name": ch["title"], "startOffset": ch["t"], "endOffset": ch["end"],
                          "url": f"https://www.youtube.com/watch?v={c['id']}&t={ch['t']}s"} for ch in c["chapters"]]
    mr = {"@context": "https://schema.org", "@type": "MusicRecording", "@id": url + "#recording", "name": t, "url": url,
          "duration": iso(c["duration"]), "byArtist": ORG, "datePublished": c["upload_date"][:10], "genre": ["Ambient", "Instrumental"],
          "image": c["thumb"], "subjectOf": {"@id": url + "#video"}, "sameAs": [f"https://www.youtube.com/watch?v={c['id']}"] + [s["url"] for s in c["stores"]]}
    return shell(rurl(c), f"{t} | Morntide", desc, "\n".join(body), [vo, mr, crumbs_ld([("Home", "/"), ("Releases", "/releases/"), (t, rurl(c))])], img=c["thumb"])
def itemlist(name, items): return {"@context": "https://schema.org", "@type": "ItemList", "name": name, "itemListOrder": "https://schema.org/ItemListOrderDescending",
                                   "numberOfItems": len(items), "itemListElement": [{"@type": "ListItem", "position": i + 1, "url": SITE + rurl(c), "name": clean_title(c["title"])} for i, c in enumerate(items)]}
def mood_links(cur=None): return '<div class="moods">' + "".join(f'<a class="btn{"" if k == cur else " ghost"}" href="/{k}/">{v[0]}</a>' for k, v in MOODS.items()) + '</div>'
def releases_index():
    body = '<p class="crumbs"><a href="/">Home</a> › Releases</p><h1>All releases</h1>' \
           f'<p class="sub">Every Morntide session on YouTube, newest first: {len(CAT)} long-form sessions for focus, mornings and sleep. Each page has the player, chapters and links to the playlists.</p>' \
           + mood_links() + '<div class="grid">' + "".join(card(c) for c in CAT) + '</div>'
    return shell("/releases/", "All releases | Morntide", "Every Morntide focus, morning and sleep session, newest first, with chapters and playlist links.", body,
                 [itemlist("Morntide releases", CAT), crumbs_ld([("Home", "/"), ("Releases", "/releases/")])])
def hub(k):
    lab, h1, intro, pls = MOODS[k]; items = [c for c in CAT if c["mood"] == k]
    body = f'<p class="crumbs"><a href="/">Home</a> › <a href="/releases/">Releases</a> › {lab.title()}</p><h1>{lab} · {e(h1)}</h1><p class="sub">{e(intro)}</p>' \
           + '<div class="actions">' + "".join(f'<a class="btn{" ghost" if i else ""}" href="https://www.youtube.com/playlist?list={p}">Open {e(PL[p]["label"])} on YouTube</a>' for i, p in enumerate(pls)) + '</div>' \
           + mood_links(k) + f'<h2>{len(items)} {lab.title()} sessions</h2><div class="grid">' + "".join(card(c) for c in items) + '</div>'
    return shell(f"/{k}/", f"{lab} — {h1} | Morntide", intro, body,
                 [{"@context": "https://schema.org", "@type": "CollectionPage", "name": f"{lab} — {h1}", "url": f"{SITE}/{k}/", "mainEntity": itemlist(f"Morntide {lab}", items)},
                  crumbs_ld([("Home", "/"), ("Releases", "/releases/"), (lab.title(), f"/{k}/")])])
PLAYER_JS = r"""
(function(){
  var D = JSON.parse(document.getElementById('mp-data').textContent), T = D.tracks;
  var $ = function(id){ return document.getElementById(id); };
  var q = '', mood = '', cur = null, loaded = false, apiPlayer = null, gen = 0;
  var want = new URLSearchParams(location.search).get('v');
  var start = T.filter(function(t){ return t.id === want; })[0] || T[0];
  function h(s){ return String(s).replace(/[&<>"]/g, function(c){ return {'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c]; }); }
  function list(){ return T.filter(function(t){ return (!mood || t.mood === mood) && (!q || t.title.toLowerCase().indexOf(q) >= 0); }); }
  var ALLOW = 'accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture; web-share';
  function drop(id){ var n = $(id); if (n) n.remove(); }
  function mark(state){ var v = $('mp-video'); if (v) v.setAttribute('data-autoplay', state); }
  function frame(src, title){
    gen++;
    if (apiPlayer && apiPlayer.destroy) { try { apiPlayer.destroy(); } catch (err) {} }
    apiPlayer = null; drop('mp-unmute'); mark('gesture');
    var f = document.createElement('iframe'); f.src = src; f.title = title;
    f.allow = ALLOW; f.allowFullscreen = true; f.referrerPolicy = 'strict-origin-when-cross-origin';
    var v = $('mp-video'); v.innerHTML = ''; v.appendChild(f);
  }
  function loadApi(ok, fail){
    if (window.YT && YT.Player) { ok(); return; }
    (loadApi.q || (loadApi.q = [])).push(ok);
    if (fail) (loadApi.fails || (loadApi.fails = [])).push(fail);
    if (loadApi.started) return;
    loadApi.started = true;
    window.YTConfig = window.YTConfig || {};
    window.YTConfig.host = 'https://www.youtube-nocookie.com';
    var prev = window.onYouTubeIframeAPIReady;
    window.onYouTubeIframeAPIReady = function(){
      if (typeof prev === 'function') { try { prev(); } catch (err) {} }
      var q = loadApi.q || []; loadApi.q = [];
      q.forEach(function(fn){ try { fn(); } catch (err) {} });
    };
    var s = document.createElement('script');
    s.src = 'https://www.youtube.com/iframe_api';
    s.async = true;
    s.onerror = function(){
      var fs = loadApi.fails || []; loadApi.fails = []; loadApi.q = [];
      fs.forEach(function(fn){ try { fn(); } catch (err) {} });
    };
    document.head.appendChild(s);
  }
  // First visit has no user gesture. Try audible autoplay; if the browser rejects it,
  // mute and keep playing, then unmute on the first tap. If even muted playback is
  // rejected, cover the same video with Tap to play so the shell never sits empty.
  function beginAutoplay(t, my){
    var v = $('mp-video');
    v.innerHTML = '';
    mark('starting');
    var src = 'https://www.youtube-nocookie.com/embed/' + encodeURIComponent(t.id)
      + '?autoplay=1&mute=0&rel=0&playsinline=1&enablejsapi=1&origin=' + encodeURIComponent(location.origin);
    var f = document.createElement('iframe');
    f.id = 'mp-frame'; f.title = t.title; f.allow = ALLOW; f.allowFullscreen = true;
    f.referrerPolicy = 'strict-origin-when-cross-origin'; f.src = src;
    v.appendChild(f);
    var player = null, triedMuted = false, settled = false, holding = false;
    function state(){ try { return player ? player.getPlayerState() : -1; } catch (err) { return -1; } }
    function audible(){ try { return !!(player && !player.isMuted() && player.getVolume() > 0); } catch (err) { return false; } }
    function showUnmute(){
      if ($('mp-unmute') || !player) return;
      var b = document.createElement('button');
      b.type = 'button'; b.className = 'mp-unmute'; b.id = 'mp-unmute'; b.textContent = 'Tap to unmute';
      b.onclick = function(){ show(cur, true); };
      v.appendChild(b);
    }
    function showBlockedTap(){
      if (holding || $('mp-tap')) return;
      holding = true; drop('mp-unmute'); mark('blocked');
      var b = document.createElement('button');
      b.type = 'button'; b.className = 'mp-tap mp-fallback'; b.id = 'mp-tap';
      b.innerHTML = '<span class="mp-pb" aria-hidden="true"><svg viewBox="0 0 24 24"><path d="M8 5v14l11-7z"/></svg></span><small>Tap to play</small><span class="sr">Play ' + h(t.title) + '</span>';
      b.onclick = function(){ show(cur, true); };
      v.appendChild(b);
    }
    function onPlaying(){
      if (my !== gen) return;
      loaded = true; holding = false; settled = true;
      if (audible()) { drop('mp-unmute'); drop('mp-tap'); mark('playing'); }
      else { drop('mp-tap'); showUnmute(); mark('muted'); }
    }
    function onBlocked(){
      if (my !== gen || holding) return;
      if (state() === 1) { onPlaying(); return; }
      if (!triedMuted) {
        triedMuted = true;
        try { if (player) { player.mute(); player.playVideo(); } } catch (err) {}
        watchdog(3000, 4);
        return;
      }
      if (state() === 3) return;
      showBlockedTap();
    }
    var watchId = 0, watchStart = Date.now();
    function watchdog(delay, buffersLeft){
      var id = ++watchId;
      setTimeout(function(){
        if (id !== watchId || my !== gen || holding || settled) return;
        var st = state();
        if (st === 1) { onPlaying(); return; }
        if (st === 3 && (Date.now() - watchStart) < 12000 && buffersLeft > 0) { watchdog(1500, buffersLeft - 1); return; }
        if (st === 3) { showBlockedTap(); return; }
        if (!triedMuted && player) {
          triedMuted = true;
          try { player.mute(); player.playVideo(); } catch (err) {}
          watchdog(3000, 2);
          return;
        }
        showBlockedTap();
      }, delay);
    }
    watchdog(8000, 6);
    loadApi(function(){
      if (my !== gen || !$('mp-frame')) return;
      try {
        apiPlayer = new YT.Player('mp-frame', {
          events: {
            onReady: function(ev){
              if (my !== gen) return;
              player = ev.target; apiPlayer = player;
              try {
                var iframe = player.getIframe();
                if (iframe) iframe.style.cssText = 'position:absolute;inset:0;width:100%;height:100%;border:0;z-index:1';
              } catch (err) {}
              // autoplay=1&mute=0 is already on the iframe URL. A second playVideo()
              // here races that request and can surface a false player error.
              var st = state();
              if (st === 1) onPlaying();
              else {
                if (st === 3) mark('buffering');
                watchdog(3000, 6);
              }
            },
            onAutoplayBlocked: onBlocked,
            onStateChange: function(ev){
              if (my !== gen || !ev) return;
              if (ev.data === 1) onPlaying();
              else if (ev.data === 3 && !settled) mark('buffering');
            },
            onError: function(){
              if (my !== gen || holding) return;
              showBlockedTap();
            }
          }
        });
      } catch (err) { if (my === gen) mark('embed'); }
    }, function(){ if (my === gen) mark('embed'); });
  }
  function show(t, play){
    var my = ++gen;
    cur = t;
    $('mp-title').textContent = t.title;
    $('mp-meta').textContent = t.moodLabel + ' · ' + t.dur + ' · ' + t.date;
    $('mp-page').href = t.page;
    $('mp-yt').href = 'https://www.youtube.com/watch?v=' + t.id;
    $('mp-stores').innerHTML = t.stores.map(function(s){ return '<a class="btn ghost" rel="noopener" href="' + h(s.url) + '">' + h(s.name) + '</a>'; }).join('');
    if (play || loaded) {
      loaded = true;
      frame('https://www.youtube-nocookie.com/embed/' + t.id + '?autoplay=1&rel=0&playsinline=1', t.title);
    } else beginAutoplay(t, my);
    render();
    if (history.replaceState) history.replaceState(null, '', '?v=' + t.id);
  }
  function step(d){ var L = list(); if (!L.length) return; var i = L.indexOf(cur); show(L[(i + d + L.length) % L.length], true); }
  function render(){
    var L = list();
    $('mp-list').innerHTML = L.length ? L.map(function(t){
      return '<li' + (t === cur ? ' class="on"' : '') + '><button type="button" data-id="' + t.id + '"' + (t === cur ? ' aria-current="true"' : '') + '>'
        + '<img src="' + h(t.thumb) + '" alt="" width="112" height="63" loading="lazy" decoding="async" /><span><b>' + h(t.title) + '</b><small>'
        + h(t.moodLabel) + ' · ' + h(t.dur) + '</small></span></button><a class="mp-rp" href="' + t.page + '">Release page</a></li>';
    }).join('') : '<li class="none">No releases match.</li>';
    [].forEach.call($('mp-list').querySelectorAll('button[data-id]'), function(b){
      b.onclick = function(){ show(T.filter(function(t){ return t.id === b.dataset.id; })[0], true); $('mp').scrollIntoView({behavior:'smooth', block:'nearest'}); };
    });
    [].forEach.call(document.querySelectorAll('.mp-chips button'), function(b){ b.setAttribute('aria-pressed', String(b.dataset.mood === mood)); });
  }
  [].forEach.call(document.querySelectorAll('.mp-chips button'), function(b){ b.onclick = function(){ mood = b.dataset.mood; render(); }; });
  [].forEach.call(document.querySelectorAll('.mp-pl'), function(b){ b.onclick = function(){
    loaded = true; frame('https://www.youtube-nocookie.com/embed/videoseries?list=' + b.dataset.list + '&autoplay=1&rel=0&playsinline=1', b.dataset.title);
    $('mp-title').textContent = b.dataset.title; $('mp-meta').textContent = 'YouTube playlist'; $('mp-stores').innerHTML = '';
    $('mp-page').href = '/' + b.dataset.mood + '/'; $('mp-yt').href = 'https://www.youtube.com/playlist?list=' + b.dataset.list;
    $('mp').scrollIntoView({behavior:'smooth', block:'nearest'});
  }; });
  $('mp-q').oninput = function(){ q = this.value.trim().toLowerCase(); render(); };
  $('mp-prev').onclick = function(){ step(-1); };
  $('mp-next').onclick = function(){ step(1); };
  show(start, false);
})();
"""
PLAYER_CSS = """
    .sr { position: absolute; width: 1px; height: 1px; overflow: hidden; clip: rect(0 0 0 0); white-space: nowrap; }
    .mp { display: grid; grid-template-columns: minmax(0, 1.35fr) minmax(0, 1fr); gap: 32px; align-items: center; margin-top: 18px; }
    .mp-video { position: relative; aspect-ratio: 16/9; border-radius: 14px; overflow: hidden; background: #000; border: 1px solid rgba(232,196,120,.25); }
    .mp-video iframe { position: absolute; inset: 0; width: 100%; height: 100%; border: 0; z-index: 1; }
    .mp-unmute { position: absolute; z-index: 3; top: 12px; left: 12px; background: var(--gold); color: var(--navy); font: inherit; font-weight: 600; font-size: 13px; letter-spacing: .04em; border: 0; border-radius: 999px; padding: 10px 16px; cursor: pointer; box-shadow: 0 6px 24px rgba(0,0,0,.45); }
    .mp-unmute:hover, .mp-unmute:focus-visible { background: var(--gold-soft); }
    .mp-unmute:focus-visible { outline: 2px solid var(--cream); outline-offset: 2px; }
    .mp-tap { all: unset; cursor: pointer; position: absolute; inset: 0; display: block; z-index: 2; }
    .mp-tap.mp-fallback { background: rgba(11,28,40,.35); }
    .mp-tap img { width: 100%; height: 100%; object-fit: cover; }
    .mp-tap small { position: absolute; left: 0; right: 0; bottom: 12px; text-align: center; font-size: 13px; color: var(--cream); text-shadow: 0 1px 4px #000; }
    .mp-pb { position: absolute; left: 50%; top: 50%; transform: translate(-50%, -50%); width: 78px; height: 78px; border-radius: 50%; background: var(--gold); display: grid; place-items: center; box-shadow: 0 6px 30px rgba(0,0,0,.55); }
    .mp-pb svg { width: 32px; height: 32px; margin-left: 4px; fill: var(--navy); }
    .mp-tap:hover .mp-pb, .mp-tap:focus-visible .mp-pb { transform: translate(-50%, -50%) scale(1.07); }
    .mp-tap:focus-visible { outline: 2px solid var(--gold); outline-offset: -2px; }
    .mp-info h2 { margin: 6px 0 10px; font-size: clamp(24px, 3vw, 34px); line-height: 1.15; }
    .mp-info .actions { margin-top: 18px; }
    .mp-pls { display: grid; grid-template-columns: repeat(auto-fill, minmax(200px, 1fr)); gap: 14px; }
    .mp-pl { all: unset; cursor: pointer; display: block; border: 1px solid rgba(232,196,120,.3); border-radius: 12px; padding: 14px 16px; background: rgba(20,38,51,.7); }
    .mp-pl b { display: block; color: var(--gold); letter-spacing: .1em; font-size: 13px; text-transform: uppercase; } .mp-pl small { color: var(--mist); font-size: 13px; }
    .mp-pl:hover, .mp-pl:focus-visible { border-color: var(--gold); }
    .mp-tools { display: flex; flex-wrap: wrap; gap: 12px; align-items: center; margin: 8px 0 16px; }
    .mp-tools input { flex: 1 1 220px; background: rgba(20,38,51,.8); color: var(--cream); border: 1px solid rgba(232,196,120,.3); border-radius: 999px; padding: 11px 18px; font: inherit; }
    .mp-chips { display: flex; flex-wrap: wrap; gap: 8px; }
    .mp-chips button { font: inherit; font-size: 13px; letter-spacing: .1em; text-transform: uppercase; cursor: pointer; color: var(--gold-soft); background: transparent; border: 1px solid rgba(232,196,120,.45); border-radius: 999px; padding: 8px 14px; }
    .mp-chips button[aria-pressed="true"] { background: var(--gold); color: var(--navy); }
    .mp-list { list-style: none; display: grid; gap: 8px; }
    .mp-list li { display: flex; align-items: center; gap: 10px; border: 1px solid rgba(232,196,120,.12); border-radius: 12px; padding: 6px 12px 6px 6px; background: rgba(20,38,51,.55); }
    .mp-list li.on { border-color: var(--gold); }
    .mp-list button { all: unset; cursor: pointer; flex: 1; display: flex; gap: 14px; align-items: center; min-width: 0; }
    .mp-list img { width: 112px; height: 63px; object-fit: cover; border-radius: 8px; flex: none; }
    .mp-list b { display: block; font-weight: 500; line-height: 1.3; } .mp-list small { color: var(--gold-soft); font-size: 13px; }
    .mp-rp { font-size: 12px; letter-spacing: .08em; text-transform: uppercase; color: var(--gold-soft); white-space: nowrap; text-decoration: underline; text-underline-offset: 3px; }
    @media (max-width: 760px) { .mp { grid-template-columns: 1fr; gap: 18px; } .mp-list img { width: 84px; height: 47px; } .mp-rp { display: none; } }
"""
def player_page():
    data = {"tracks": [{"id": c["id"], "title": clean_title(c["title"]), "mood": c["mood"], "moodLabel": MOODS[c["mood"]][0], "dur": human(c["duration"]),
                        "date": c["upload_date"][:10], "thumb": c["thumb"], "page": rurl(c), "stores": c["stores"]} for c in CAT]}
    pls = [(p, k) for k, v in MOODS.items() for p in v[3]]
    body = ('<p class="crumbs"><a href="/">Home</a> › Music Player</p><h1>Music Player</h1>'
            '<p class="sub">Play every Morntide session and playlist in one place. Pick a mood, press play, stay with one task.</p>'
            '<section class="mp" id="mp" aria-label="Now playing"><div class="mp-video" id="mp-video"></div>'
            '<div class="mp-info"><p class="kicker">Now playing</p><h2 id="mp-title"></h2><p class="meta" id="mp-meta"></p>'
            '<div class="actions"><button type="button" class="btn ghost" id="mp-prev" aria-label="Previous">⏮</button><button type="button" class="btn ghost" id="mp-next" aria-label="Next">⏭</button>'
            '<a class="btn" id="mp-page" href="/releases/">Release page</a><a class="btn ghost" id="mp-yt" href="https://www.youtube.com/@Morntidemusic">YouTube</a></div>'
            '<div class="actions" id="mp-stores"></div>'
            '<div class="actions"><a class="btn ghost" href="https://www.youtube.com/@Morntidemusic/live">● Focus Radio live</a></div></div></section>'
            '<h2>Playlists</h2><div class="mp-pls">' + "".join(
                f'<button type="button" class="mp-pl" data-list="{p}" data-mood="{k}" data-title="{e(PL[p]["label"])} playlist"><b>{e(PL[p]["label"])}</b><small>{MOODS[k][0].title()} · play on YouTube</small></button>' for p, k in pls) + '</div>'
            '<h2>Releases</h2><div class="mp-tools"><label class="sr" for="mp-q">Search releases</label><input id="mp-q" type="search" placeholder="Search releases" />'
            '<div class="mp-chips" role="group" aria-label="Moods"><button type="button" data-mood="">All</button>' + "".join(f'<button type="button" data-mood="{k}">{v[0]}</button>' for k, v in MOODS.items()) + '</div></div>'
            '<ul class="mp-list" id="mp-list"></ul><noscript><div class="grid">' + "".join(card(c) for c in CAT) + '</div></noscript>'
            f'<script id="mp-data" type="application/json">{json.dumps(data, ensure_ascii=False).replace("</", "<\\/")}</script>'
            f'<style>{PLAYER_CSS}</style><script>{PLAYER_JS}</script>')
    return shell("/player/", "Music Player | Morntide", "Play every Morntide focus, morning and sleep session and playlist in one player.", body,
                 [{"@context": "https://schema.org", "@type": "WebPage", "name": "Morntide Music Player", "url": SITE + "/player/"},
                  crumbs_ld([("Home", "/"), ("Music Player", "/player/")])])
def notfound():
    body = '<h1>Page not found</h1><p class="sub">That page drifted out with the tide. Try the releases or one of the moods.</p>' + mood_links() + '<div class="actions"><a class="btn" href="/releases/">All releases</a><a class="btn ghost" href="/">Home</a></div>'
    return shell("/404.html", "Page not found | Morntide", "Page not found.", body, [], robots="noindex")
def home():
    h = src_index
    for vid, c in BYID.items(): h = h.replace("{{rel:%s}}" % vid, rurl(c))
    assert "{{rel:" not in h, "home links a video that is not in the catalog"
    latest = ('  <section class="latest" id="latest">\n    <div class="wrap">\n      <p class="kicker">New on the channel</p>\n      <h2>Latest releases</h2>\n'
              '      <div class="grid">' + "".join(card(c) for c in CAT[:6]) + '</div>\n'
              '      <div class="actions"><a class="btn" href="/releases/">All releases</a><a class="btn ghost" href="/focus/">Focus</a><a class="btn ghost" href="/rise/">Rise</a><a class="btn ghost" href="/sleep/">Sleep</a></div>\n    </div>\n  </section>')
    h = h.replace("<!--LATEST-RELEASES-->", latest, 1)
    return h.replace("</style>", EXTRA + "</style>", 1)
def sitemap():
    u = [(SITE + "/", CAT[0]["upload_date"][:10], "1.0", ""), (SITE + "/releases/", CAT[0]["upload_date"][:10], "0.9", ""), (SITE + "/player/", CAT[0]["upload_date"][:10], "0.8", "")]
    for k in MOODS:
        it = [c for c in CAT if c["mood"] == k]; u.append((f"{SITE}/{k}/", it[0]["upload_date"][:10] if it else CAT[0]["upload_date"][:10], "0.8", ""))
    for c in CAT:
        v = (f"<video:video><video:thumbnail_loc>{e(c['thumb'])}</video:thumbnail_loc><video:title>{e(c['title'])}</video:title>"
             f"<video:description>{e(first_text(c))}</video:description><video:player_loc>https://www.youtube-nocookie.com/embed/{c['id']}</video:player_loc>"
             f"<video:duration>{c['duration']}</video:duration><video:publication_date>{c['upload_date']}</video:publication_date><video:family_friendly>yes</video:family_friendly></video:video>")
        u.append((SITE + rurl(c), c["upload_date"][:10], "0.7", v))
    return ('<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9" xmlns:video="http://www.google.com/schemas/sitemap-video/1.1">\n'
            + "".join(f"  <url><loc>{l}</loc><lastmod>{m}</lastmod><priority>{p}</priority>{v}</url>\n" for l, m, p, v in u) + "</urlset>\n")

def w(rel, s): f = D / rel; f.parent.mkdir(parents=True, exist_ok=True); f.write_text(s)
if D.exists(): shutil.rmtree(D)
for p in R.rglob("*"):
    rel = p.relative_to(R)
    if p.is_dir() or rel.parts[0] in SKIP or "node_modules" in rel.parts: continue
    if any(x.startswith(".") for x in rel.parts): continue
    if str(rel) in NOCOPY or p.suffix in NONSITE_EXT or p.name in {"package.json", "package-lock.json"}: continue
    out = D / rel; out.parent.mkdir(parents=True, exist_ok=True); shutil.copy2(p, out)
w("index.html", home())
w("releases/index.html", releases_index())
for k in MOODS: w(f"{k}/index.html", hub(k))
for c in CAT: w(f"releases/{c['slug']}/index.html", release(c))
w("player/index.html", player_page())
w("404.html", notfound())
spa = BYID.get("U78G7IYZ51o")
w("_redirects", (f"/spa-bowls {rurl(spa)} 301\n/spa-bowls/ {rurl(spa)} 301\n" if spa else ""))
w("sitemap.xml", sitemap())
# Mobile menu (<760px), same pattern as djchezerecta: a menu button that reveals every nav link, on every page.
MENU_BTN = ('<button type="button" class="mbtn" aria-label="Menu" aria-expanded="false" aria-controls="site-nav">'
            '<svg width="24" height="24" viewBox="0 0 24 24" aria-hidden="true" focusable="false"><path d="M3 6h18M3 12h18M3 18h18" stroke="currentColor" stroke-width="2.2" stroke-linecap="round"/></svg></button>')
MENU_CSS = ('<style>.mbtn{display:none;background:transparent;border:1px solid rgba(232,196,120,.45);color:var(--gold-soft);border-radius:10px;width:44px;height:44px;'
            'align-items:center;justify-content:center;cursor:pointer;margin-left:auto}.mbtn:focus-visible{outline:2px solid var(--gold);outline-offset:2px}'
            '@media (max-width:760px){nav .wrap{flex-wrap:wrap;position:relative}.mbtn{display:inline-flex}nav ul#site-nav{display:none}'
            'nav.open ul#site-nav{display:flex;flex-direction:column;gap:0;order:10;width:100%;padding:6px 0 10px}'
            'nav.open ul#site-nav a{display:block;padding:13px 4px;border-top:1px solid rgba(232,196,120,.14);font-size:15px}}</style>')
MENU_JS = ('<script>(function(){var n=document.querySelector("nav"),b=n&&n.querySelector(".mbtn");if(!b)return;'
           'function set(o){n.classList.toggle("open",o);b.setAttribute("aria-expanded",String(o));b.setAttribute("aria-label",o?"Close menu":"Menu")}'
           'b.addEventListener("click",function(){set(!n.classList.contains("open"))});'
           'n.querySelectorAll("#site-nav a").forEach(function(a){a.addEventListener("click",function(){set(false)})});'
           'document.addEventListener("keydown",function(e){if(e.key==="Escape"&&n.classList.contains("open")){set(false);b.focus()}})})();</script>')
def add_menu(h):
    if 'class="mbtn"' in h or "<nav>" not in h: return h
    nav = h.index("<nav>"); ul = h.index("<ul>", nav)
    h = h[:ul] + MENU_BTN + '<ul id="site-nav">' + h[ul + 4:]
    return h.replace("</head>", MENU_CSS + "</head>", 1).replace("</body>", MENU_JS + "</body>", 1)
# GA4 + fail-closed checks
for f in D.rglob("*.html"):
    if re.fullmatch(r"google[0-9a-f]+\.html", f.name): continue
    h = add_menu(f.read_text()); f.write_text(h)
    for blk in re.findall(r'<script type="application/ld\+json">(.*?)</script>', h, re.S): json.loads(blk)
    if SNIP and GA not in h: h = h.replace("</head>", SNIP + "</head>", 1); f.write_text(h)
sm = (D / "sitemap.xml").read_text()
for c in CAT:
    assert (D / f"releases/{c['slug']}/index.html").exists() and SITE + rurl(c) in sm, f"release check failed: {c['id']}"
print(f"built {D}: {len(CAT)} release pages, 3 mood hubs, releases index, music player, 404, sitemap ({sm.count('<url>')} urls)")
