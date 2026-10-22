#!/usr/bin/env python3
"""Refresh data/*.json from the public Morntide YouTube channel (fail-closed).
catalog.json  every public, non-live, non-Short, non-scheduled long-form upload (+chapters, mood, verified store links)
shorts.json   public Shorts with the long-form video their description links to (parent)
playlists.json mood playlists and their video ids
Source: yt-dlp (channel /videos, /shorts, playlists + per-video -J). YTDLP_META_DIR=dir reuses fresh (<24 h) `yt-dlp -J` files.
A video is excluded unless yt-dlp confirms availability=public and live_status not live/upcoming/was_live.
Zero videos or a listing error aborts without writing anything."""
import json, os, pathlib, re, subprocess, sys, time, urllib.request
R = pathlib.Path(__file__).resolve().parent.parent; D = R / "data"
CH = "https://www.youtube.com/channel/UCjIlIYsKiIyUOVsHpItKOWA"
PLAYLISTS = {  # id -> (label, mood).  Rule order for a video's mood: FOCUS/RISE/SLEEP playlists, then Deep Work Blocks, then RELAX/First Light, else SLEEP
  "PLUp6gLFHAa3E": ("FOCUS", "focus"), "PLSmZ4mxAy_Sg": ("RISE", "rise"), "PLF2-pms8eUrY": ("SLEEP", "sleep"),
  "PLe1cGzmYaAX0": ("Deep Work Blocks", "focus"), "PLKj69vZNgz7s": ("RELAX", "rise"), "PLH3nuFmJ72Ds": ("First Light Sessions", "rise")}
ORDER = list(PLAYLISTS)
SLUGS = {}
META = os.environ.get("YTDLP_META_DIR")
STORE_RE = r"https?://(?:open\.spotify\.com|music\.apple\.com|music\.amazon\.com|music\.youtube\.com|distrokid\.com/hyperfollow)[^\s)\"']*"
STORE_NAME = [("open.spotify.com", "Spotify"), ("music.apple.com", "Apple Music"), ("music.youtube.com", "YouTube Music"),
              ("music.amazon.com", "Amazon Music"), ("distrokid.com", "Pre-save")]
UA = {"User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/124 Safari/537.36"}

def die(m): print("ABORT:", m, file=sys.stderr); sys.exit(1)
def ytdlp(*a):
    p = subprocess.run(["yt-dlp", "--no-warnings", *a], capture_output=True, text=True, timeout=300)
    if p.returncode: raise RuntimeError(p.stderr.strip()[-300:])
    return json.loads(p.stdout)
def flat(url): return ytdlp("--flat-playlist", "-J", url).get("entries") or []
def meta(vid, short=False):
    if META:
        f = pathlib.Path(META) / (("s_" if short else "") + vid + ".json")
        if f.exists() and time.time() - f.stat().st_mtime < 86400: return json.loads(f.read_text())
    return ytdlp("-J", "--skip-download", ("https://www.youtube.com/shorts/" if short else "https://www.youtube.com/watch?v=") + vid)
def get(url):
    try:
        with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=20) as r: return r.status, r.read(400000).decode("utf8", "ignore")
    except Exception as e: return getattr(e, "code", 0), ""
def is_public(m): return m.get("availability") == "public" and m.get("live_status") in (None, "not_live")
STOP = {"a","an","the","of","for","to","and","in","on","with","your","this","that","you","will","keep","me","my","is","it",
        "hour","hours","hr","hrs","minutes","min","no","listen","need","playlist","morntide","music","best","perfect","1","2","3","8","53","one"}
def slugify(t):
    """Short, keyword-led slug (3-5 words). Only used for a NEW video; data/slugs.json pins every slug forever."""
    t = re.sub(r"\s*[|·]\s*Morntide\s*$", "", t, flags=re.I).lower().replace("&", " ")
    w = [x for x in re.findall(r"[a-z0-9]+", t) if x not in STOP]
    return "-".join(w[:4]) or "release"
def thumb(vid):
    for q in ("maxresdefault", "sddefault", "hqdefault"):
        u = f"https://i.ytimg.com/vi/{vid}/{q}.jpg"
        if get(u)[0] == 200: return u
    return f"https://i.ytimg.com/vi/{vid}/hqdefault.jpg"
def stores(desc, title):
    """Keep a store link only when its live page title names Morntide (album/track pages) -- verified, never guessed."""
    out, seen = [], set()
    for u in re.findall(STORE_RE, desc or ""):
        u = u.rstrip(".,")
        name = next((n for h, n in STORE_NAME if h in u), None)
        if not name or name in seen: continue
        chk = re.sub(r"open\.spotify\.com/(album|track)/", r"open.spotify.com/embed/\1/", u)  # Spotify pages are JS-only; the embed page is server-rendered
        code, html = get(chk)
        t = re.search(r"<title[^>]*>(.*?)</title>", html, re.S | re.I)
        t = t.group(1) if t else ""
        if code == 200 and ("morntide" in t.lower() or "morntide" in html[:200000].lower()):
            out.append({"name": name, "url": u}); seen.add(name)
        else: print(f"  store link dropped (unverified {code}): {u}", file=sys.stderr)
    return sorted(out, key=lambda x: [n for _, n in STORE_NAME].index(x["name"]))

def main():
    try:
        longs = flat(CH + "/videos"); shorts = flat(CH + "/shorts")
        pls = {p: [e["id"] for e in flat("https://www.youtube.com/playlist?list=" + p)] for p in PLAYLISTS}
    except Exception as e: die(f"listing failed: {e}")
    if not longs: die("zero long-form videos")
    old = {}
    SLUGS.update(json.loads((D / "slugs.json").read_text()) if (D / "slugs.json").exists() else {})
    if (D / "catalog.json").exists(): old = {c["id"]: c for c in json.loads((D / "catalog.json").read_text())}
    cat, slugs = [], set()
    for e in longs:
        vid = e["id"]
        try: m = meta(vid)
        except Exception as x: print(f"  skip {vid}: metadata error {x}", file=sys.stderr); continue
        if not is_public(m) or (m.get("duration") or 0) < 180: print(f"  skip {vid}: not public long-form", file=sys.stderr); continue
        inpl = [p for p in ORDER if vid in pls[p]]
        mood = PLAYLISTS[inpl[0]][1] if inpl else "sleep"
        slug = SLUGS.get(vid)   # data/slugs.json pins every slug: URLs never change
        if not slug:
            slug = slugify(m["title"])
            while slug in slugs or slug in SLUGS.values(): slug += "-" + re.sub(r"[^a-z0-9]", "", vid.lower())[:4]
            SLUGS[vid] = slug; print(f"  new slug {vid} -> {slug}", file=sys.stderr)
        if slug in slugs: die(f"duplicate slug {slug}")
        slugs.add(slug)
        ts = m.get("timestamp") or 0
        cat.append({"id": vid, "slug": slug, "title": m["title"], "description": m.get("description") or "",
                    "duration": int(m.get("duration") or 0), "timestamp": ts,
                    "upload_date": time.strftime("%Y-%m-%dT%H:%M:%S+00:00", time.gmtime(ts)),
                    "chapters": [{"t": int(c["start_time"]), "end": int(c["end_time"]), "title": c["title"]} for c in (m.get("chapters") or [])],
                    "mood": mood, "playlists": inpl, "thumb": old.get(vid, {}).get("thumb") or thumb(vid),
                    "stores": stores(m.get("description"), m["title"])})
    if not cat: die("zero public long-form videos after status check")
    ids = {c["id"] for c in cat}; sh = []
    for e in shorts:
        try: m = meta(e["id"], short=True)
        except Exception: continue
        if not is_public(m): continue
        par = [v for v in re.findall(r"(?:youtu\.be/|[?&]v=)([A-Za-z0-9_-]{11})", m.get("description") or "") if v in ids]
        sh.append({"id": e["id"], "title": m["title"], "parent": par[0] if par else None})
    cat.sort(key=lambda c: -c["timestamp"])
    D.mkdir(exist_ok=True)
    (D / "catalog.json").write_text(json.dumps(cat, ensure_ascii=False, indent=1))
    (D / "slugs.json").write_text(json.dumps(SLUGS, ensure_ascii=False, indent=1))
    (D / "shorts.json").write_text(json.dumps(sh, ensure_ascii=False, indent=1))
    (D / "playlists.json").write_text(json.dumps([{"id": p, "label": PLAYLISTS[p][0], "mood": PLAYLISTS[p][1], "ids": pls[p]} for p in ORDER], indent=1))
    print(f"catalog: {len(cat)} releases, {len(sh)} shorts ({sum(1 for s in sh if s['parent'])} linked)")
main()
